import pdfplumber
import docx
import os
import asyncio
from beanie import PydanticObjectId
from app.models.document import DocumentModel
from app.services.vector_db import vector_db_service
import logging

logger = logging.getLogger(__name__)

class ExtractorService:
    """
    Service responsible for extracting text from raw document files.
    """
    
    @staticmethod
    def extract_pdf_text(file_path: str) -> str:
        """
        Extracts raw text from a PDF file using pdfplumber.
        This is a synchronous CPU-bound function.
        """
        extracted_text = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # extract_text() pulls the text out while attempting to respect the layout
                    text = page.extract_text()
                    if text:
                        extracted_text.append(text)
            
            return "\n\n".join(extracted_text)
        except Exception as e:
            logger.error(f"Failed to extract PDF text from {file_path}: {str(e)}")
            raise e

    @staticmethod
    def extract_docx_text(file_path: str) -> str:
        """
        Extracts raw text from a DOCX file using python-docx.
        """
        try:
            doc = docx.Document(file_path)
            extracted_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    extracted_text.append(para.text)
            
            return "\n\n".join(extracted_text)
        except Exception as e:
            logger.error(f"Failed to extract DOCX text from {file_path}: {str(e)}")
            raise e

    @staticmethod
    def extract_image_text(file_path: str) -> str:
        """
        Extracts raw text from an image using EasyOCR.
        """
        try:
            # We import and initialize EasyOCR lazily here because loading the ML model
            # into memory takes a few seconds and we don't want to slow down FastAPI startup.
            import easyocr
            
            # Initialize the reader (English only for now). 
            # In a real app we might cache this reader instance globally.
            reader = easyocr.Reader(['en'])
            
            # EasyOCR returns a list of tuples: (bbox, text, confidence)
            results = reader.readtext(file_path)
            
            extracted_text = []
            for (bbox, text, prob) in results:
                extracted_text.append(text)
                
            return "\n".join(extracted_text)
        except Exception as e:
            logger.error(f"Failed to extract text from image {file_path}: {str(e)}")
            raise e

    @staticmethod
    async def process_document_background(document_id: PydanticObjectId, file_path: str):
        """
        Background task to extract text and update the database status.
        Because pdfplumber is CPU-bound and synchronous, we run it in a threadpool
        so it doesn't block the async FastAPI event loop.
        """
        # Fetch the document from DB
        doc = await DocumentModel.get(document_id)
        if not doc:
            logger.error(f"Document {document_id} not found for background processing.")
            return

        try:
            # Run the synchronous CPU-bound text extraction in a separate thread!
            loop = asyncio.get_event_loop()
            
            if doc.mime_type == "application/pdf":
                extracted_text = await loop.run_in_executor(None, ExtractorService.extract_pdf_text, file_path)
            elif doc.mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
                extracted_text = await loop.run_in_executor(None, ExtractorService.extract_docx_text, file_path)
            elif doc.mime_type in ["image/jpeg", "image/png", "image/jpg"]:
                extracted_text = await loop.run_in_executor(None, ExtractorService.extract_image_text, file_path)
            else:
                extracted_text = "Unsupported file type for extraction yet."
            
            # We have the text, now let's detect the language!
            # It's fast, so we don't need a separate thread for it.
            detected_lang = "en"  # Default fallback
            if extracted_text.strip():
                try:
                    from langdetect import detect
                    detected_lang = detect(extracted_text)
                except Exception as lang_e:
                    logger.warning(f"Could not detect language for doc {document_id}, defaulting to en: {str(lang_e)}")
                    
            # Save the extracted text to a .txt file next to the original file
            text_file_path = file_path + ".txt"
            with open(text_file_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
                
            # --- NEW WEEK 4 LOGIC: Vector Database Ingestion ---
            # Send the text to ChromaDB for chunking and embedding!
            # We run this in the background thread too so it doesn't block the API.
            try:
                metadata = {
                    "filename": doc.filename,
                    "mime_type": doc.mime_type,
                    "language": detected_lang
                }
                vector_db_service.add_document(
                    document_id=str(doc.id), 
                    text=extracted_text, 
                    metadata=metadata
                )
            except Exception as vdb_e:
                logger.error(f"Failed to ingest document into vector db: {vdb_e}")
                
            # Update the document status to completed and save the language
            doc.processing_status = "completed"
            doc.language = detected_lang
            await doc.save()
            logger.info(f"Successfully processed document {document_id}")
            
        except Exception as e:
            doc.processing_status = "failed"
            doc.error_message = str(e)
            
            await doc.save()
            logger.error(f"Failed processing document {document_id}: {str(e)}")

extractor_service = ExtractorService()
