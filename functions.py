import os
import httpx
import json
import pdfplumber
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))

OUTPUTS_FOLDER = r"C:\Users\crist\Documents\CRISTIAN\FACULTATE\INFORMATICA ECONOMICA\ANUL V\LICENTA\PROIECT\ExtrAct\outputs"

class ExtractedTerm(BaseModel):
    topic: str = Field(description="The broad topic, e.g., 'Obligations - Supplier', 'Termination', or 'Dispute Resolution'.")
    details: str = Field(description="Telegraphic facts about this category (max 10 words)")
    source_article: Optional[str]

class ContractSummary(BaseModel):
    contract_title: Optional[str]
    parties: List[ExtractedTerm]
    effective_date: Optional[str]
    initial_duration_months: Optional[int]
    obligations: List[ExtractedTerm]
    termination: List[ExtractedTerm]
    liability: List[ExtractedTerm]
    dispute_resolution: List[ExtractedTerm]

def extract_text_from_pdf(file_bytes) -> str:
    text=""
    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def get_formatting_instruction(format_type: str) -> str:
    
    if format_type == "paragraphs":
        return (
            "Structure the answer in three cohesive, smooth, free-flowing, but short, tight, condensed paragraphs. "
            "Group related information into logical sections. "
            "The first paragraph will provide context by presenting topic, parties, effective data, term."
            "The second paragraph will focus on the main obligations."
            "The third paragraph will analyse termination, liability, disputes."
            "Reference articles after each extracted term in the following format: (Article xy)."
        )
    
    elif format_type == "bullet points":
        return (
            "Present the information as a clean list of key facts. "
            "Use broad headers and list details under them. "
            "Be telegraphic. Avoid full sentences where fragments suffice. The more succint, the better. "
            "Reference articles after each extracted term in the following format: (Article xy)."
        )
    
    elif format_type == "json":
        return (
            "Extract the requested data into the strict JSON schema provided. "
            "All text values should be telegraphic (10 words maximum). "
            "Adhere to international standards (e.g. ISO8601) to enhance machine readability. "
        )
    
    else:
        return "Output Format: Concise Summary."

def summarize_text(text: str, output_format: str) -> str:

    instructions = get_formatting_instruction(output_format);

    prompt = ("You are a highly precise Legal Document Review Assistant. " 
              "Your sole function is stripping away technical legalese to extract the FACTS from the provided contract in a concise manner. " 
              "Pay special attention to elements such as Contract Title, Parties, Effective Date, Term, Obligations, Termination, Liability, Dispute Resolution."
              "You do not, by any means, provide legal advice or interpretation; you provide structured, FACTUAL reports to executives and non-lawyers. "
              "If a material term is missing from the text, refrain from addressing it rather than guessing. "
              "If the provided document does not represent a contract, you must necessarily exclusively and explicitly state 'Please provide a valid contract.' " 
              "Do not include an introduction or a conclusion. Do not paste full clauses. "
              "Use standard UTC8 characters only and basic '-'. "
              f"The structure of the generated report should adhere to the following instructions: {instructions}. "
              f"The provided contract is: \n\n{text}")

    if output_format == "json":
        response = client.beta.chat.completions.parse(
            model="gpt-5.1", 
            temperature=0,
            messages=[{"role":"user", "content": prompt}],
            response_format=ContractSummary
        )
        summary = response.choices[0].message.parsed.model_dump_json(exclude_none=False)
        return summary
    else:
        response = client.chat.completions.create(
            model="gpt-5.1",
            temperature=0,
            messages=[{"role":"user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        return summary

def save_summary(summary: str, session_id: str) -> str:
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") # converts datetime to string
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, session_id)
    os.makedirs(USER_FOLDER, exist_ok=True)
    filepath = os.path.join(USER_FOLDER, f"summary_{timestamp}.txt")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(summary)
    return filepath

def save_summary_pdf(summary: str, session_id: str) -> str:
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    USER_FOLDER = os.path.join(OUTPUTS_FOLDER, session_id)
    os.makedirs(USER_FOLDER, exist_ok=True)
    filepath = os.path.join(USER_FOLDER, f"summary_{timestamp}.pdf")

    doc = SimpleDocTemplate(filepath, pagesize = letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50) # generates a pdf document

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = 'Times-Roman'
    styles["Normal"].fontSize = 12
    content = []

    if summary.strip().startswith("{"):
        summary = json.dumps(json.loads(summary), indent=2).replace(" ", "&nbsp;")
    
    content.append(Paragraph(summary.replace("\n", "<br/>"), styles["Normal"]))
                   
    doc.build(content)

    return filepath

async def post_summary_to_server(summary_json: str):
    async with httpx.AsyncClient() as client:
        payload = json.loads(summary_json)
        response = await client.post("http://localhost:4000/summaries", json=payload)
        response.raise_for_status()
        return response.json()



