"""
LangChain agent service implementation
"""
from typing import Optional, Dict, Any
import structlog
from core.config import settings

logger = structlog.get_logger(__name__)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.tools import Tool
    from langchain import hub
except ImportError as e:
    logger.warning(f"Failed to import LangChain dependencies: {e}")
    # Define dummy classes to prevent NameError at module level
    ChatGoogleGenerativeAI = None
    AgentExecutor = None
    create_react_agent = None
    Tool = None
    hub = None


class AgentService:
    """Service for creating and executing LangChain agents"""

    def __init__(self):
        """Initialize agent service with LLM and tools"""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
            
        if not ChatGoogleGenerativeAI:
            raise ImportError("LangChain dependencies are missing. Install them to use AgentService.")

        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7
        )

        # Define tools
        self.tools = self._create_tools()

    def _create_tools(self) -> list: # Changed return type hint to generic list to avoid NameError if Tool is None
        """Create tools for the agent"""

        def search_tool(query: str) -> str:
            """Placeholder search tool"""
            return f"Search results for: {query}"

        def calculator_tool(expression: str) -> str:
            """Simple calculator tool"""
            try:
                result = eval(expression)
                return f"Result: {result}"
            except Exception as e:
                return f"Error: {str(e)}"
        
        if not Tool:
             return []

        tools = [
            Tool(
                name="Search",
                func=search_tool,
                description="Useful for searching information. Input should be a search query."
            ),
            Tool(
                name="Calculator",
                func=calculator_tool,
                description="Useful for mathematical calculations. Input should be a mathematical expression."
            )
        ]

        return tools

    async def execute(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None
    ) -> dict:
        """
        Execute agent with given prompt

        Args:
            prompt: User prompt
            context: Additional context
            max_iterations: Maximum agent iterations

        Returns:
            Execution result with intermediate steps
        """
        try:
            if not hub or not create_react_agent or not AgentExecutor:
                 raise ImportError("LangChain dependencies missing")

            # Get prompt template
            react_prompt = hub.pull("hwchase17/react")

            # Create agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=react_prompt
            )

            # Create executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=max_iterations or settings.MAX_ITERATIONS,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )

            # Add context to prompt if provided
            if context:
                prompt = f"Context: {context}\n\nUser request: {prompt}"

            # Execute agent
            result = await agent_executor.ainvoke({"input": prompt})

            return {
                "result": result.get("output", ""),
                "intermediate_steps": [
                    {
                        "action": step[0].tool,
                        "input": step[0].tool_input,
                        "output": step[1]
                    }
                    for step in result.get("intermediate_steps", [])
                ],
                "total_tokens": None  # Can be extracted from callbacks if needed
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            raise
