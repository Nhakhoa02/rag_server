import httpx
import structlog
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from pydantic.v1 import SecretStr
from app.core.config import settings

logger = structlog.get_logger()

class LLMService:
    """LLM service supporting Gemini only"""
    
    def __init__(self):
        self.llm = None
        self.llm_provider = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM based on configuration and available API keys"""
        try:
            # Check for Gemini API key
            if settings.gemini_api_key:
                logger.info("Initializing Gemini LLM", model=settings.llm_model)
                self.llm = ChatGoogleGenerativeAI(
                    api_key=SecretStr(settings.gemini_api_key),
                    model=settings.llm_model,
                    temperature=0.1,
                    convert_system_message_to_human=True
                )
                self.llm_provider = "gemini"
            else:
                logger.warning("No Gemini API key available - LLM functionality disabled")
                self.llm_provider = "none"
                
        except Exception as e:
            logger.error("Failed to initialize LLM", error=str(e))
            self.llm = None
            self.llm_provider = "none"
    
    async def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate response using RAG"""
        try:
            if not self.llm:
                return "LLM service is not available. Please configure a Gemini API key."
            
            # Prepare context
            context_text = self._prepare_context(context)
            
            # Create system prompt
            system_prompt = """You are a helpful AI assistant that answers questions based on the provided context. 
            Always base your answers on the context provided. If the context doesn't contain enough information 
            to answer the question, say so. Be concise and accurate in your responses."""
            
            # Create user prompt
            user_prompt = f"""Context: {context_text}

Question: {query}

Please answer the question based on the context provided above."""
            
            # Generate response
            messages: List[BaseMessage] = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.agenerate([messages])
            answer = response.generations[0][0].text
            
            logger.info("LLM response generated", 
                       query_length=len(query),
                       context_chunks=len(context),
                       response_length=len(answer),
                       llm_provider=self.llm_provider)
            
            return answer.strip()
            
        except Exception as e:
            logger.error("Failed to generate LLM response", 
                        query=query,
                        error=str(e))
            return f"Sorry, I encountered an error while generating a response: {str(e)}"
    
    def _prepare_context(self, context: List[Dict[str, Any]]) -> str:
        """Prepare context for LLM"""
        context_parts = []
        
        for i, item in enumerate(context, 1):
            content = item.get('content', '')
            metadata = item.get('metadata', {})
            
            # Add source information
            source_info = f"Source {i}: "
            if metadata.get('file_id'):
                source_info += f"Document {metadata['file_id']}"
            if metadata.get('chunk_index') is not None:
                source_info += f" (Chunk {metadata['chunk_index'] + 1}/{metadata.get('total_chunks', 1)})"
            
            context_parts.append(f"{source_info}\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _get_provider_name(self) -> str:
        """Get the current LLM provider name"""
        return self.llm_provider or "none"
    
    async def test_connection(self) -> bool:
        """Test LLM connection"""
        try:
            if not self.llm:
                return False
                
            test_query = "Hello, this is a test message."
            test_messages: List[BaseMessage] = [HumanMessage(content=test_query)]
            response = await self.llm.agenerate([test_messages])
            return bool(response.generations[0][0].text)
                
        except Exception as e:
            logger.error("LLM connection test failed", error=str(e))
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get LLM model information"""
        try:
            if self.llm_provider == "gemini":
                return {
                    'provider': 'gemini',
                    'model': settings.llm_model,
                    'type': 'chat',
                    'api_key_configured': bool(settings.gemini_api_key),
                    'status': 'available' if self.llm else 'unavailable'
                }
            else:
                return {
                    'provider': 'none',
                    'model': 'none',
                    'type': 'none',
                    'api_key_configured': False,
                    'status': 'unavailable',
                    'message': 'No LLM provider configured. Please set GEMINI_API_KEY environment variable.'
                }
                
        except Exception as e:
            logger.error("Failed to get model info", error=str(e))
            return {
                'provider': 'unknown',
                'model': 'unknown',
                'type': 'unknown',
                'api_key_configured': False,
                'status': 'error',
                'error': str(e)
            } 