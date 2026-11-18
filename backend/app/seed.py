"""
seed.py — Demo account and sample documents.

Creates   demo@dochub.dev / demo12345   with seven realistic district-office documents
(DOCX, PDF, TXT, one in Malayalam). Dates are written relative to today, so the
calendar always has upcoming deadlines. Runs automatically on startup when SEED_DEMO=true
and the demo user does not exist yet; can also be run manually:  python -m app.seed
"""

import asyncio
import hashlib
import io
import logging
import os
import textwrap
from datetime import datetime, timedelta

from app.core.auth.hashing import get_password_hash
from app.models.document import DocumentModel
from app.models.user import User
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@dochub.dev"
DEMO_PASSWORD = "demo12345"


def _d(days: int, fmt: str = "%d %B %Y") -> str:
    return (datetime.utcnow() + timedelta(days=days)).strftime(fmt)


def _docs() -> list[dict]:
    return [
        {
            "filename": "Finance Circular - Utilisation Certificates FY 2026-27.docx",
            "kind": "docx",
            "paragraphs": [
                "GOVERNMENT OF KERALA — FINANCE (BUDGET) DEPARTMENT",
                "Circular No. FIN/B2/482/2026",
                "Subject: Submission of Utilisation Certificates for grants released in FY 2026-27",
                "All Heads of Departments and District Collectors are informed that grants-in-aid released during the "
                "first and second quarters of the financial year 2026-27 must be accounted for through Utilisation "
                "Certificates (UCs) in the prescribed Form 12-C.",
                f"Utilisation Certificates for all grants above Rs. 5 lakh must be submitted on or before {_d(12)} to the "
                "Finance (Budget) Department through the BIMS portal.",
                f"A review meeting of all Drawing and Disbursing Officers will be held on {_d(5)} at 11:00 AM in the "
                "Finance Department conference hall, Government Secretariat, Thiruvananthapuram.",
                "Departments that fail to furnish UCs within the deadline will not be eligible for release of the "
                "third-quarter instalment. Unspent balances must be remitted to the treasury with interest.",
                f"The balance amount of unspent funds must be remitted to the treasury not later than {_d(26)}.",
                "The Accountant General (A&E) Kerala will audit a random sample of ten percent of certificates. "
                "Expenditure statements must reconcile with treasury records.",
                "Principal Secretary (Finance)",
            ],
        },
        {
            "filename": "Tender Notice - Road Resurfacing Works, Kochi.pdf",
            "kind": "pdf",
            "paragraphs": [
                "PUBLIC WORKS DEPARTMENT — ROADS DIVISION, ERNAKULAM",
                "e-Tender Notice No. PWD/EKM/R/77/2026",
                "Name of work: Resurfacing and drainage improvement of the Kaloor - Kadavanthra Road (4.2 km), Kochi.",
                "Online bids are invited from registered PWD contractors of Class A and above for the above work. "
                "Estimated contract value: Rs. 3.86 crore. Period of completion: 9 months.",
                f"A pre-bid meeting will be held on {_d(8)} at 3:00 PM in the office of the Executive Engineer, PWD Roads "
                "Division, Ernakulam.",
                f"The last date for online submission of bids is {_d(20)} up to 5:00 PM. Technical bids will be opened "
                f"on {_d(22)}.",
                f"Earnest Money Deposit (EMD) of Rs. 2,00,000 must be paid online on or before {_d(19)}.",
                "Bidders must upload scanned copies of their registration certificate, GST registration, and audited "
                "financial statements for the last three years. The contractor shall maintain the road for a "
                "defect liability period of five years. Payment will be released in stages against measured work "
                "after verification by the Assistant Engineer.",
                "Executive Engineer, PWD Roads Division, Ernakulam",
            ],
        },
        {
            "filename": "Monsoon Preparedness Plan - Ernakulam District.docx",
            "kind": "docx",
            "paragraphs": [
                "DISTRICT DISASTER MANAGEMENT AUTHORITY, ERNAKULAM",
                "Monsoon and Flood Preparedness Plan — Action Points",
                "The District Disaster Management Authority (DDMA) has reviewed flood risk across Aluva, Paravur and "
                "Kothamangalam taluks. Low-lying wards along the Periyar river remain the most vulnerable.",
                f"All local bodies must complete cleaning of drains, canals and culverts on or before {_d(10)} and report "
                "completion to the DDMA control room.",
                f"A mock evacuation drill will be held on {_d(15)} in Aluva municipality, coordinated by Fire and Rescue "
                "Services and the Revenue Department.",
                "Relief camps must be identified in every village with drinking water, sanitation and medical support. "
                "The Health Department will station medical teams and stock ORS, antibiotics and anti-snake venom.",
                "Village Officers must update the list of vulnerable families, including elderly people living alone, "
                "persons with disabilities and pregnant women, for priority evacuation.",
                f"The next DDMA review meeting is scheduled for {_d(6)} at the Collectorate.",
                "District Collector & Chairperson, DDMA",
            ],
        },
        {
            "filename": "പ്രളയ ദുരിതാശ്വാസ കിറ്റ് വിതരണം - സർക്കുലർ.txt",
            "kind": "txt",
            "text": "\n\n".join([
                "കേരള സർക്കാർ — ജില്ലാ കളക്ടറേറ്റ്, എറണാകുളം",
                "സർക്കുലർ നമ്പർ: DM/1245/2026",
                "വിഷയം: പ്രളയ ദുരിതാശ്വാസ കിറ്റ് വിതരണം — നിർദ്ദേശങ്ങൾ",
                "ജില്ലയിലെ പ്രളയബാധിത പ്രദേശങ്ങളിലെ കുടുംബങ്ങൾക്ക് ദുരിതാശ്വാസ കിറ്റുകൾ വിതരണം ചെയ്യുന്നതിനുള്ള നിർദ്ദേശങ്ങൾ താഴെ നൽകുന്നു.",
                f"1. എല്ലാ വില്ലേജ് ഓഫീസർമാരും അർഹരായ കുടുംബങ്ങളുടെ പട്ടിക {_d(9, '%d/%m/%Y')} തീയതിക്കകം താലൂക്ക് ഓഫീസിൽ സമർപ്പിക്കേണ്ടതാണ്.",
                f"2. കിറ്റ് വിതരണം {_d(14, '%d/%m/%Y')} മുതൽ റേഷൻ കടകൾ വഴി ആരംഭിക്കും.",
                f"3. വിതരണ പുരോഗതി അവലോകനം ചെയ്യുന്നതിനുള്ള യോഗം {_d(17, '%d/%m/%Y')} ന് രാവിലെ 11 മണിക്ക് കളക്ടറേറ്റ് കോൺഫറൻസ് ഹാളിൽ ചേരും.",
                "4. ഓരോ കിറ്റിലും അരി, പയർ, വെളിച്ചെണ്ണ, കുടിവെള്ളം, അവശ്യ മരുന്നുകൾ എന്നിവ ഉൾപ്പെടുത്തണം.",
                "5. പരാതികൾ ജില്ലാ ദുരന്ത നിവാരണ അതോറിറ്റിയുടെ കൺട്രോൾ റൂമിൽ (ഫോൺ: 1077) അറിയിക്കാവുന്നതാണ്.",
                "ജില്ലാ കളക്ടർ, എറണാകുളം",
            ]),
        },
        {
            "filename": "IT Services Agreement - e-Office Maintenance.docx",
            "kind": "docx",
            "paragraphs": [
                "SERVICE LEVEL AGREEMENT",
                "This Agreement is entered into between the Kerala State IT Mission (hereinafter 'KSITM') and "
                "Keltron Software Services Ltd (hereinafter 'the Service Provider') for annual maintenance of the "
                "e-Office file management system deployed across 84 government offices.",
                f"This Agreement shall take effect from {_d(-20)} and remain valid until {_d(345)}, unless terminated "
                "earlier under Clause 14.",
                "The Service Provider shall guarantee 99.5% monthly uptime, resolve priority-1 incidents within four "
                "hours, and provide on-site support engineers at the State Data Centre.",
                f"The first quarterly payment of Rs. 18,40,000 is due on {_d(24)} against submission of the uptime report "
                "and invoice. Subsequent payments fall due every quarter.",
                "All data processed under this Agreement remains the property of the Government of Kerala and must be "
                "stored within India. The Service Provider shall comply with the IT Act, 2000 and CERT-In directions.",
                f"A quarterly performance review will be held on {_d(30)} at KSITM, Thiruvananthapuram.",
                "Signed for KSITM — Director;  Signed for the Service Provider — Chief Executive Officer",
            ],
        },
        {
            "filename": "Minutes - District Health Review Meeting.txt",
            "kind": "txt",
            "text": "\n\n".join([
                "MINUTES OF THE DISTRICT HEALTH REVIEW MEETING — ERNAKULAM",
                f"Date of meeting: {_d(-6)}.  Chaired by: District Medical Officer (Health).",
                "Members present: Deputy DMO, District Programme Manager (NHM), Medical Officers of 12 PHCs, "
                "representatives of the DDMA and the Kerala Water Authority.",
                "1. Fever surveillance: Dengue and leptospirosis cases have risen in Aluva and Paravur after early "
                "monsoon rains. Field teams will intensify source-reduction drives and doxycycline prophylaxis for "
                "flood-relief workers.",
                f"2. The measles-rubella catch-up vaccination drive will begin on {_d(11)} in all PHCs. Medical Officers "
                f"must submit micro-plans on or before {_d(4)}.",
                "3. Relief camps: The Health Department will station medical teams at relief camps identified by "
                "the DDMA and keep stocks of ORS, antibiotics and anti-snake venom.",
                "4. Drinking water: The Kerala Water Authority will chlorinate wells in flood-affected wards.",
                f"5. The next review meeting will be held on {_d(21)} at the District Medical Office.",
                "Action taken report to be circulated to all members within one week.",
            ]),
        },
        {
            "filename": "Post-Matric Scholarship Notification 2026.txt",
            "kind": "txt",
            "text": "\n\n".join([
                "DIRECTORATE OF COLLEGIATE EDUCATION, KERALA",
                "Notification: Post-Matric Scholarship for Higher Education, 2026-27",
                "Applications are invited from students belonging to economically weaker sections who are enrolled "
                "in government and aided colleges for the Post-Matric Scholarship scheme. Annual family income must "
                "not exceed Rs. 2.5 lakh.",
                f"The last date to apply online through the e-Grantz portal is {_d(28)}.",
                f"Institutions must verify and forward applications not later than {_d(35)}.",
                "Students must upload their income certificate, community certificate, Aadhaar-linked bank account "
                "details and the previous year's mark list. Scholarship amounts will be credited directly to the "
                "student's bank account through DBT.",
                "For queries, contact the scholarship cell of the Directorate of Collegiate Education.",
            ]),
        },
    ]


def _make_docx(paragraphs: list[str]) -> bytes:
    import docx

    d = docx.Document()
    for i, p in enumerate(paragraphs):
        if i == 0:
            d.add_heading(p, level=1)
        else:
            d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _make_pdf(paragraphs: list[str]) -> bytes:
    """Minimal single-font PDF writer (no extra dependency)."""
    lines: list[str] = []
    for p in paragraphs:
        lines.extend(textwrap.wrap(p, 92) or [""])
        lines.append("")
    per_page = 48
    pages = [lines[i : i + per_page] for i in range(0, len(lines), per_page)]

    def esc(s: str) -> str:
        s = s.replace("—", "-").replace("–", "-").replace("’", "'").replace("“", '"').replace("”", '"')
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")

    objs: list[bytes] = []
    n_pages = len(pages)
    page_ids = [4 + i * 2 for i in range(n_pages)]
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in page_ids)}] /Count {n_pages} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, page in enumerate(pages):
        stream = "BT /F1 10.5 Tf 15 TL 56 790 Td " + " ".join(f"({esc(l)}) Tj T*" for l in page) + " ET"
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_ids[i] + 1} 0 R >>".encode()
        )
        data = stream.encode("latin-1")
        objs.append(b"<< /Length " + str(len(data)).encode() + b" >>\nstream\n" + data + b"\nendstream")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "txt": "text/plain",
}


async def seed_demo(force: bool = False):
    from app.core.ingestion.pipeline import process_document

    try:
        user = await User.find_one(User.email == DEMO_EMAIL)
        if user and not force:
            return
        if not user:
            user = User(email=DEMO_EMAIL, hashed_password=get_password_hash(DEMO_PASSWORD),
                        full_name="Demo Officer", role="manager")
            await user.insert()
        logger.info("[SEED] Creating demo documents for %s", DEMO_EMAIL)

        created = []
        for i, spec in enumerate(_docs()):
            if spec["kind"] == "docx":
                data = _make_docx(spec["paragraphs"])
            elif spec["kind"] == "pdf":
                data = _make_pdf(spec["paragraphs"])
            else:
                data = spec["text"].encode("utf-8")
            digest = hashlib.sha256(data).hexdigest()
            path = os.path.join(storage_service.base_dir, f"{digest}.{spec['kind']}")
            with open(path, "wb") as f:
                f.write(data)
            doc = DocumentModel(
                filename=spec["filename"], file_size=len(data), mime_type=MIME[spec["kind"]],
                file_hash=digest, storage_path=path, uploaded_by=str(user.id),
                uploaded_at=datetime.utcnow() - timedelta(hours=len(_docs()) - i),
            )
            await doc.insert()
            created.append(doc)

        for doc in created:
            await process_document(doc.id, base_date=datetime.utcnow())
        logger.info("[SEED] Demo data ready (%d documents)", len(created))
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("[SEED] Failed to seed demo data")


if __name__ == "__main__":
    from app.db.init_db import init_mongodb

    async def _main():
        await init_mongodb()
        await seed_demo(force=False)

    asyncio.run(_main())
