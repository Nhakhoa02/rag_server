import httpx
import structlog
from typing import List, Dict, Any, Optional
from langchain.llms import Ollama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, BaseMessage
from pydantic import SecretStr
from app.core.config import settings

logger = structlog.get_logger()

class LLMService:
    """LLM service supporting multiple providers (Gemini, OpenAI, Ollama)"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM based on configuration and available API keys"""
        # Priority order: Gemini > OpenAI > Ollama
        
        # Try Gemini first
        if settings.gemini_api_key:
            logger.info("Initializing Gemini LLM", model=settings.llm_model)
            return ChatGoogleGenerativeAI(
                google_api_key=SecretStr(settings.gemini_api_key),
                model=settings.llm_model,
                temperature=0.1,
                convert_system_message_to_human=True
            )
        
        
        # Fallback to Ollama
        else:
            logger.info("Initializing Ollama LLM", model=settings.llm_model)
            return Ollama(
                base_url=settings.ollama_base_url,
                model=settings.llm_model,
                temperature=0.1
            )
    
    async def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate response using RAG"""
        try:
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
            
            # Generate response based on LLM type
            if isinstance(self.llm, ChatGoogleGenerativeAI):
                # For Gemini
                gemini_messages: List[BaseMessage] = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = await self.llm.agenerate([gemini_messages])
                answer = response.generations[0][0].text
                
            elif isinstance(self.llm, ChatOpenAI):
                # For OpenAI
                openai_messages: List[BaseMessage] = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = await self.llm.agenerate([openai_messages])
                answer = response.generations[0][0].text
                
            else:
                # For Ollama
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = await self.llm.agenerate([full_prompt])
                answer = response.generations[0][0].text
            
            logger.info("LLM response generated", 
                       query_length=len(query),
                       context_chunks=len(context),
                       response_length=len(answer),
                       llm_provider=self._get_provider_name())
            
            return answer.strip()
            
        except Exception as e:
            logger.error("Failed to generate LLM response", 
                        query=query,
                        error=str(e))
            raise
    
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
        if isinstance(self.llm, ChatGoogleGenerativeAI):
            return "gemini"
        elif isinstance(self.llm, ChatOpenAI):
            return "openai"
        else:
            return "ollama"
    
    async def test_connection(self) -> bool:
        """Test LLM connection"""
        try:
            test_query = "Hello, this is a test message."
            
            if isinstance(self.llm, ChatGoogleGenerativeAI):
                test_messages: List[BaseMessage] = [HumanMessage(content=test_query)]
                response = await self.llm.agenerate([test_messages])
                return bool(response.generations[0][0].text)
                
            else:
                # For Ollama
                response = await self.llm.agenerate([test_query])
                return bool(response.generations[0][0].text)
                
        except Exception as e:
            logger.error("LLM connection test failed", error=str(e))
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get LLM model information"""
        try:
            if isinstance(self.llm, ChatGoogleGenerativeAI):
                return {
                    'provider': 'gemini',
                    'model': settings.llm_model,
                    'type': 'chat',
                    'api_key_configured': bool(settings.gemini_api_key)
                }
                
            elif isinstance(self.llm, ChatOpenAI):
                return {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'type': 'chat',
                    'api_key_configured': bool(settings.openai_api_key)
                }
                
            else:
                # For Ollama, try to get model info
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{settings.ollama_base_url}/api/tags")
                        if response.status_code == 200:
                            models = response.json().get('models', [])
                            current_model = next((m for m in models if m['name'] == settings.llm_model), None)
                            
                            return {
                                'provider': 'ollama',
                                'model': settings.llm_model,
                                'type': 'completion',
                                'model_info': current_model,
                                'api_key_configured': True  # Ollama doesn't need API key
                            }
                except:
                    pass
                
                return {
                    'provider': 'ollama',
                    'model': settings.llm_model,
                    'type': 'completion',
                    'api_key_configured': True
                }
                
        except Exception as e:
            logger.error("Failed to get model info", error=str(e))
            return {
                'provider': 'unknown',
                'model': 'unknown',
                'type': 'unknown',
                'api_key_configured': False
            } 