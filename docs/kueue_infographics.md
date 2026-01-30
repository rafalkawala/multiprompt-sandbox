# Kueue: Kubernetes-Native Job Queueing

This document explains how **Kueue** works, moving from a high-level architectural view to low-level parameters and functionality.

## 1. High-Level Architecture: The "Traffic Controller" for Batch Jobs

Kueue acts as a gatekeeper for your Kubernetes cluster. Standard Kubernetes schedulers schedule *Pods* as soon as they are created. Kueue manages *Jobs* (collections of Pods) and decides **when** they should start, ensuring you don't overshoot your quotas or overload the cluster.

```mermaid
graph TD
    subgraph Users
        U1[Data Scientist A]
        U2[ML Engineer B]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Kueue Layer (The Gatekeeper)"
            LQ[Local Queues]
            CQ[Cluster Queue]
            Logic{Admit?}
        end

        subgraph "Standard K8s Layer"
            API[K8s API Server]
            Sched[Kube Scheduler]
            Nodes[Worker Nodes]
        end
    end

    U1 -->|Submit PyTorchJob| API
    U2 -->|Submit Batch Job| API
    API -.->|Intercepted| LQ
    LQ --> CQ
    CQ --> Logic
    Logic -- "✅ Quota Available" --> API
    API -->|Create Pods| Sched
    Sched -->|Place Pods| Nodes
    Logic -- "❌ No Quota" --> LQ
    LQ -.->|Wait / Pending| LQ

    style Logic fill:#f96,stroke:#333,stroke-width:2px
    style CQ fill:#bbf,stroke:#333,stroke-width:2px
    style Sched fill:#bfb,stroke:#333,stroke-width:2px
```

### Key Takeaways
*   **Users** submit standard K8s Jobs (e.g., `Job`, `MPIJob`, `RayJob`).
*   **Kueue** suspends them immediately (they don't create Pods yet).
*   **Kueue** only "admits" (unsuspends) the Job when the **ClusterQueue** has enough quota.

---

## 2. Core Concepts & Hierarchy

Kueue separates the *submission* of jobs (namespaced) from the *allocation* of resources (cluster-wide).

```mermaid
classDiagram
    direction TB
    class ResourceFlavor {
        +Labels (e.g. region, gpu-model)
        +Taints
    }

    class ClusterQueue {
        +Cohort (Resource Sharing Group)
        +ResourceGroups
        +Usage Limits
    }

    class LocalQueue {
        +Namespace (Team A)
        +Reference -> ClusterQueue
    }

    class Workload {
        +Job Spec
        +Priority
    }

    ResourceFlavor "1" <-- "*" ClusterQueue : Uses
    ClusterQueue "1" <-- "*" LocalQueue : Points to
    LocalQueue "1" <-- "*" Workload : Submitted to

    note for LocalQueue "Acts as the entry point for a Team's jobs.\nResides in the Team's Namespace."
    note for ClusterQueue "Manages Quotas across multiple teams.\nGlobal scope."
    note for ResourceFlavor "Describes the 'Physical' nature of the resource\n(e.g., 'spot-p4d-24xlarge')."
```

### The Objects
1.  **ResourceFlavor**: Describes *what* the resource is (e.g., "Spot Instance", "NVIDIA A100"). It doesn't define quantity, just the "flavor".
2.  **ClusterQueue**: Defines *how much* of a Flavor exists and *who* can use it. It is the central engine for quotas.
3.  **LocalQueue**: A namespaced pointer to a ClusterQueue. Users submit to this.
4.  **Workload**: The internal representation of a Job inside Kueue.

---

## 3. Low-Level Flow: Admission & Parameters

How does Kueue decide to run a job? It uses a complex calculation involving **Nominal Quotas**, **Borrowing**, and **Cohorts**.

### The Admission Loop

```mermaid
sequenceDiagram
    participant User
    participant JobController
    participant KueueWebhook
    participant Workload
    participant ClusterQueue
    participant K8sScheduler

    User->>JobController: 1. Apply Job (suspended=true)
    JobController->>KueueWebhook: 2. Create Workload
    KueueWebhook->>Workload: 3. Create object in LocalQueue

    loop Every Cycle
        Workload->>ClusterQueue: 4. Request Admission
        ClusterQueue->>ClusterQueue: 5. Check Quota
        alt Fits in Nominal Quota?
            ClusterQueue->>Workload: ✅ Admit
        else Fits in Borrowing Limit (Cohort)?
            ClusterQueue->>Workload: ✅ Admit (Borrowed)
        else No Quota
            ClusterQueue->>Workload: ⏳ Keep Pending
        end
    end

    Workload->>JobController: 6. Update Job Status (unsuspend)
    JobController->>K8sScheduler: 7. Create Pods
```

### Critical Parameters Visualization

Imagine a **Cohort** named `ResearchTeam` shared by two ClusterQueues: `TeamA` and `TeamB`.

```mermaid
block-beta
    columns 3

    block:TeamA
        A_Nominal["Nominal Quota: 10 GPUs"]
        A_Usage[("Current Usage: 12 GPUs")]
        A_Status["Status: BORROWING"]
    end

    block:SharedResource
        Cohort(("Cohort: 'ResearchTeam'"))
        Pool["Unused Quota Pool"]
    end

    block:TeamB
        B_Nominal["Nominal Quota: 10 GPUs"]
        B_Usage[("Current Usage: 2 GPUs")]
        B_Status["Status: LENDING"]
    end

    A_Nominal --> Cohort
    B_Nominal --> Cohort
    B_Usage -- "8 Unused" --> Pool
    Pool -- "2 Borrowed" --> A_Usage

    style A_Status fill:#f99
    style B_Status fill:#9f9
```

### Parameter Explanations

| Parameter | Location | Description |
| :--- | :--- | :--- |
| **`nominalQuota`** | `ClusterQueue` | The guaranteed baseline resources for this queue. The queue can always use up to this amount. |
| **`borrowingLimit`** | `ClusterQueue` | How much *extra* the queue can take from the Cohort if others aren't using it. If `0`, it can never exceed `nominalQuota`. |
| **`cohort`** | `ClusterQueue` | A string identifier. All ClusterQueues with the same `cohort` name share their unused `nominalQuota` with each other. |
| **`reclaimWithinCohort`** | `ClusterQueue` | If `Any`, a queue can preempt (kill) jobs in other queues in the same cohort if it needs its `nominalQuota` back. |
| **`preemption`** | `ClusterQueue` | Controls logic for killing lower priority jobs to make room for higher priority ones (within the same queue or across the cluster). |

### Example Config Snippet
```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: team-a-cq
spec:
  namespaceSelector: {} # Matches all namespaces
  cohort: "research-pool" # Joins the shared pool
  resourceGroups:
  - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
    flavors:
    - name: "on-demand"
      resources:
      - name: "nvidia.com/gpu"
        nominalQuota: 10    # Guaranteed 10 GPUs
        borrowingLimit: 5   # Can borrow up to 5 more (Total 15 max)
```
