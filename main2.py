from fastapi import FastAPI, UploadFile, File, Form
from fastapi import Request
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.templating import Jinja2Templates
from functions import extract_text_from_pdf, summarize_text, save_summary, save_summary_pdf, post_summary_to_server
import uvicorn
import io
import os

templates = Jinja2Templates(directory="templates")

app = FastAPI(title="ExtrAct")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/summarize", response_class=PlainTextResponse)
async def summarize_pdf(
    file: UploadFile = File(...),
    output_format: str = Form(...),
    session_id: str = Form(...)):
    
    if not file.filename.lower().endswith(".pdf"):
        return "Error: Only PDF files are supported."
    
    pdf_bytes = await file.read()
    pdf_file = io.BytesIO(pdf_bytes)
    
    try:
        text = extract_text_from_pdf(pdf_file)
        if not text:
            return "Error: PDF contains no extractable text."
    except Exception as e:
        return f"Error reading PDF: {e}"
    
    try:
        summary = summarize_text(text, output_format)
    except Exception as e:
        return f"Error summarizing text: {e}"
    
    errors = []

    try:
        save_summary(summary,session_id)
    except Exception as e:
        errors.append(f"TXT save failed: {str(e)}")
    
    try:
        save_summary_pdf(summary,session_id)
    except Exception as e:
        errors.append(f"PDF save failed: {str(e)}")

    if output_format == "json":
        try:
            await post_summary_to_server(summary)
        except Exception as e:
            errors.append(f"JSON Server save failed: {str(e)}")

    if errors:
        print(f"Warnings: {', '.join(errors)}")
    
    return summary

@app.get("/downloadtxt")
def download_txt_summary(session_id: str):
    OUTPUTS_FOLDER = r"C:\Users\crist\Documents\CRISTIAN\FACULTATE\INFORMATICA ECONOMICA\ANUL V\LICENTA\PROIECT\ExtrAct\outputs"
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, session_id)

    list_of_files = [f for f in os.listdir(USER_FOLDER) if f.endswith(".txt")]

    if not list_of_files:
        return "Error: No txt summaries available for download."

    latest_file = max(
        list_of_files, key=lambda x: os.path.getctime(os.path.join(USER_FOLDER, x))
    )

    file_path = os.path.join(USER_FOLDER, latest_file) 

    return FileResponse(file_path, media_type='text/plain', filename=latest_file)

@app.get("/downloadpdf")
def download_pdf_summary(session_id : str):
    OUTPUTS_FOLDER = r"C:\Users\crist\Documents\CRISTIAN\FACULTATE\INFORMATICA ECONOMICA\ANUL V\LICENTA\PROIECT\ExtrAct\outputs"
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, session_id)

    list_of_files = [f for f in os.listdir(USER_FOLDER) if f.endswith(".pdf")]

    if not list_of_files:
        return "Error: No pdf summaries available for download."
    
    latest_file = max(
        list_of_files, key=lambda x: os.path.getctime(os.path.join(USER_FOLDER, x))
    )

    file_path = os.path.join(USER_FOLDER, latest_file)

    return FileResponse(file_path, media_type='application/pdf', filename=latest_file)

@app.get("/filehistory")
def filehistory(session_id: str):
    OUTPUTS_FOLDER = r"C:\Users\crist\Documents\CRISTIAN\FACULTATE\INFORMATICA ECONOMICA\ANUL V\LICENTA\PROIECT\ExtrAct\outputs"
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, session_id)

    list_of_files = [f for f in os.listdir(USER_FOLDER)]

    list_of_files.sort(key=lambda x: os.path.getctime(os.path.join(USER_FOLDER, x)), reverse=True)
    
    # skips the first two (the most recent txt file and the most recent pdf file) !!! GENERATION FAILURE
    
    list_of_files_except_latest = list_of_files[2:]

    return {"files": list_of_files_except_latest}

@app.get("/download_old_file")
def download_old_file(session_id: str, filename: str):
    OUTPUTS_FOLDER = r"C:\Users\crist\Documents\CRISTIAN\FACULTATE\INFORMATICA ECONOMICA\ANUL V\LICENTA\PROIECT\ExtrAct\outputs"
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, os.path.basename(session_id))

    file_path = os.path.join(USER_FOLDER, os.path.basename(filename))

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)
        

@app.delete("/delete_file")
def delete_file(session_id: str, filename: str):
    OUTPUTS_FOLDER = r"C:\Users\crist\Documents\CRISTIAN\FACULTATE\INFORMATICA ECONOMICA\ANUL V\LICENTA\PROIECT\ExtrAct\outputs"
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, os.path.basename(session_id))

    file_path = os.path.join(USER_FOLDER, os.path.basename(filename))

    try:
        os.remove(file_path)
        return {"status":"success", "message": f"{filename} deleted."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def main():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()