import os
import subprocess
import pytesseract
import fitz
from PIL import Image
import io
import logging
from config.config import ALLOWED_EXTENSIONS, TESSERACT_CMD

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Ρύθμιση Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def allowed_file(filename):
    """
    Ελέγχει αν η επέκταση του αρχείου είναι αποδεκτή.
    
    Args:
        filename: Το όνομα του αρχείου
        
    Returns:
        bool: True εάν η επέκταση είναι αποδεκτή, False διαφορετικά
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """
    Εξάγει κείμενο από ένα αρχείο PDF χρησιμοποιώντας PyMuPDF και καλώντας απευθείας το Tesseract.
    
    Args:
        pdf_path: Η διαδρομή του αρχείου PDF
        
    Returns:
        str: Το εξαγόμενο κείμενο
    """
    full_text = ""
    tesseract_dir = os.path.dirname(TESSERACT_CMD) 
    tessdata_path = os.path.join(tesseract_dir, 'tessdata')
    
    # Ρύθμιση TESSDATA_PREFIX
    os.environ['TESSDATA_PREFIX'] = tessdata_path
    logger.debug(f"Setting TESSDATA_PREFIX='{tessdata_path}'")
    
    try:
        # Έλεγχος αν το αρχείο υπάρχει
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return f"[Error: PDF file not found at {pdf_path}]"
            
        logger.info(f"Starting OCR processing for: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        logger.info(f"PDF has {total_pages} pages")
        
        for page_num in range(total_pages):
            logger.info(f"Processing page {page_num+1}/{total_pages}")
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            try:
                # Προετοιμασία της εντολής tesseract
                command = [
                    TESSERACT_CMD,
                    'stdin',
                    'stdout',
                    '-l', 'eng+ell',
                    '--psm', '3'
                ]
                
                # Εκτέλεση της εντολής με subprocess
                result = subprocess.run(
                    command, 
                    input=img_bytes, 
                    capture_output=True, 
                    check=False,
                    env=os.environ
                )

                # Έλεγχος για σφάλματα από το tesseract
                if result.returncode != 0:
                    stderr_output = result.stderr.decode('utf-8', errors='replace')
                    logger.error(f"Tesseract command failed on page {page_num + 1} with error code {result.returncode}: {stderr_output}")
                    page_text = f"[Tesseract Execution Error on page {page_num + 1}]\n"
                else:
                    # Επιτυχής εκτέλεση
                    page_text = result.stdout.decode('utf-8', errors='replace')
                    text_length = len(page_text)
                    logger.info(f"Successfully extracted {text_length} characters from page {page_num+1}")
                    # Έλεγχος για κενό κείμενο
                    if text_length < 10:  # Αν έχει λιγότερους από 10 χαρακτήρες, πιθανώς δεν βρέθηκε κείμενο
                        logger.warning(f"Very little text extracted from page {page_num+1}, possibly empty or non-text PDF")

                full_text += page_text + "\n\n--- Page Break ---\n\n"

            except FileNotFoundError:
                logger.error(f"TESSERACT NOT FOUND at: {TESSERACT_CMD}. OCR failed for page {page_num + 1}.")
                full_text += f"[OCR Error: Tesseract executable not found for page {page_num + 1}]\n"
            except Exception as subproc_err:
                logger.error(f"Subprocess error on page {page_num + 1}: {subproc_err}")
                full_text += f"[OCR Subprocess Error on page {page_num + 1}: {subproc_err}]\n"

        doc.close()
        total_extracted = len(full_text)
        logger.info(f"OCR completed. Total text extracted: {total_extracted} characters")
        
        # Έλεγχος για κενό ή πολύ μικρό κείμενο συνολικά
        if total_extracted < 50:
            logger.warning(f"Very little text extracted from entire PDF ({total_extracted} chars). Check if PDF contains actual text or if OCR failed.")
            
        return full_text
    except Exception as e:
        logger.error(f"Error opening or processing PDF {pdf_path}: {e}")
        return f"[Error processing PDF: {e}]" 