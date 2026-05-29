import os
import time

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama

from app.config import get_settings
from app.logger import logger
from app.exceptions import (
    LLMError,
    VectorDBError,
    InvalidQueryError
)


def ask_question(query: str) -> dict:
    """
    Hybrid RAG + LLM reasoning pipeline.
    Uses retrieved documents as primary context
    while allowing LLM general reasoning.
    """

    settings = get_settings()

    start_time = time.time()

    try:

        # -----------------------------
        # Validate Query
        # -----------------------------
        if not query or not query.strip():
            raise InvalidQueryError(
                "Query cannot be empty"
            )

        logger.info(f"Processing query: {query}")

        # -----------------------------
        # Check Vector DB
        # -----------------------------
        if not os.path.exists(settings.VECTOR_DB_PATH):

            logger.warning(
                "Vector DB not found"
            )

            return {
                "response": (
                    "No documents have been uploaded yet. "
                    "Please upload a PDF first."
                ),
                "sources": [],
                "retrieved_chunks": 0,
                "latency_seconds": round(
                    time.time() - start_time,
                    2
                )
            }

        # -----------------------------
        # Load Embeddings
        # -----------------------------
        try:

            embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL
            )

            db = FAISS.load_local(
                settings.VECTOR_DB_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )

            logger.info(
                "Vector database loaded"
            )

        except Exception as e:

            logger.error(
                f"Vector DB load failed: {str(e)}"
            )

            raise VectorDBError(str(e))

        # -----------------------------
        # Retrieve Documents
        # -----------------------------
        try:

            retriever = db.as_retriever(
                search_kwargs={
                    "k": settings.RETRIEVER_K
                }
            )

            docs = retriever.invoke(query)

            logger.info(
                f"Retrieved {len(docs)} chunks"
            )

        except Exception as e:

            logger.error(
                f"Retrieval failed: {str(e)}"
            )

            raise VectorDBError(str(e))

        # -----------------------------
        # Build Context
        # -----------------------------
        context = ""

        if docs:

            context = "\n\n".join([
                doc.page_content
                for doc in docs
            ])

        # -----------------------------
        # Build Hybrid Prompt
        # -----------------------------
        prompt = f"""
You are an advanced enterprise AI assistant.

Your goal is to provide intelligent,
accurate, and helpful answers.

You must follow these rules:

1. Use retrieved document context as PRIMARY source
2. Use your own reasoning and general knowledge as SECONDARY support
3. If context partially answers the question,
   expand intelligently
4. If context is missing information,
   still provide a useful answer using general AI knowledge
5. Clearly mention when information comes
   from general reasoning instead of uploaded documents
6. Be concise, professional, and accurate
7. Never hallucinate fake facts from documents

Retrieved Context:
{context}

User Question:
{query}

Helpful Answer:
"""

        # -----------------------------
        # Call LLM
        # -----------------------------
        try:

            logger.info(
                "Generating LLM response"
            )

            llm = Ollama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.4
            )

            response = llm.invoke(prompt)

            logger.info(
                "LLM response generated"
            )

        except Exception as e:

            logger.error(
                f"LLM failed: {str(e)}"
            )

            raise LLMError(str(e))

        # -----------------------------
        # Extract Sources
        # -----------------------------
        sources = []

        for doc in docs:

            filename = doc.metadata.get(
                "source",
                "Unknown"
            )

            page = doc.metadata.get(
                "page",
                "Unknown"
            )

            sources.append(
                f"{filename} - Page {page}"
            )

        # -----------------------------
        # Final Response
        # -----------------------------
        latency = round(
            time.time() - start_time,
            2
        )

        logger.info(
            f"Request completed in {latency}s"
        )

        return {
            "response": response,
            "sources": list(set(sources)),
            "retrieved_chunks": len(docs),
            "latency_seconds": latency
        }

    except InvalidQueryError as e:

        logger.warning(str(e))
        raise

    except (VectorDBError, LLMError):
        raise

    except Exception as e:

        logger.error(
            f"Unexpected error: {str(e)}"
        )

        raise LLMError(str(e))