"""
Parser for the PDF417 barcode on the back of a DoD Common Access Card (CAC).

Reference: DoD-ID Bar Code SDK Formats v7.5.0 (Sep 2012)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

BRANCH_CODES = {
    "A": "USA", "C": "USCG", "D": "DOD", "F": "USAF", "H": "USPHS",
    "M": "USMC", "N": "USN", "O": "NOAA", "1": "Foreign Army",
    "2": "Foreign Navy", "3": "Foreign Marine Corps", "4": "Foreign Air Force",
    "X": "Other",
}

PDT_CODES = {
    "S": "Social Security Number (SSN)",
    "N": "9 digits, not valid SSN",
    "P": "Special code before SSNs",
    "D": "Temporary Identifier Number (TIN)",
    "F": "Foreign Identifier Number (FIN)",
    "T": "Test (858 series)",
    "I": "Individual Taxpayer Identification Number",
}

CATEGORY_CODES = {
    "A": "Active Duty member", "B": "Presidential Appointee",
    "C": "DoD civil service employee", "D": "100% disabled American veteran",
    "E": "DoD contract employee", "F": "Former member",
    "G": "National Guard member", "H": "Medal of Honor recipient",
    "I": "Non-DoD Civil Service Employee", "J": "Academy student",
    "K": "Non-appropriated fund (NAF) DoD employee", "L": "Lighthouse service",
    "M": "Non-Government agency personnel", "N": "National Guard member",
    "O": "Non-DoD contract employee",
    "Q": "Reserve retiree not yet eligible for retired pay",
    "R": "Retired Uniformed Service member eligible for retired pay",
    "S": "Reserve", "T": "Foreign military member", "U": "Foreign national employee",
    "V": "Reserve member", "W": "DoD Beneficiary", "Y": "Retired DoD Civil Service Employees",
}


def get_branch(code: str) -> str:
    return BRANCH_CODES.get(code, "N/A")


def get_pdt(code: str) -> str:
    return PDT_CODES.get(code, "N/A")


def get_category(code: str) -> str:
    return CATEGORY_CODES.get(code, "N/A")


@dataclass
class CACHolder:
    """Parsed identity data pulled from a CAC PDF417 barcode."""
    first_name: str
    last_name: str
    middle_initial: str
    rank: str
    barcode_version: str
    instance_id: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class BarcodeFormatError(ValueError):
    """Raised when scanned data doesn't match the expected CAC barcode format."""


def _read(data: str, count: int) -> Tuple[str, str]:
    return data[:count], data[count:]


def parse_cac_barcode(data: str) -> CACHolder:
    """Parse the raw PDF417 payload scanned off the back of a CAC."""
    if len(data) < 88:
        raise BarcodeFormatError("Barcode data is shorter than expected.")

    version, data = _read(data, 1)
    if version not in ("1", "N", "M"):
        raise BarcodeFormatError(f"Unsupported barcode version: {version!r}")

    # Skip PDI (6) + PDT (1) + EDIPI (8)
    _, data = _read(data, 15)

    raw_name, data = _read(data, 46)
    raw_name = re.sub(r"^[^A-Za-z]+", "", raw_name)
    first = re.sub(r"[^A-Za-z\s]", "", raw_name[:20]).strip()
    last = re.sub(r"[^A-Za-z\s]", "", raw_name[20:]).strip()
    first = re.sub(r"\s+[A-Z]$", "", first).strip()  # drop stray middle initial

    # Skip DOB (4) + PCC (1) + Branch (1) + PECT (2)
    _, data = _read(data, 8)

    raw_rank, data = _read(data, 10)
    rank = raw_rank.strip()
    if "NF00" in rank:
        rank = rank.split("NF00")[-1].strip()

    # Skip Pay Plan (2) + Grade (2) + Issue date (4) + Expiration date (4)
    _, data = _read(data, 12)

    instance_id, data = _read(data, 1)

    middle_initial = ""
    if version != "1":
        middle_raw, data = _read(data, 1)
        middle_clean = middle_raw.strip()
        if re.fullmatch(r"[A-Z]", middle_clean):
            middle_initial = middle_clean

    return CACHolder(
        first_name=first,
        last_name=last,
        middle_initial=middle_initial,
        rank=rank,
        barcode_version=version,
        instance_id=instance_id,
    )
