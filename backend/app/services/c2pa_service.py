import json
from pathlib import Path
from typing import List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.schemas.evidence import ProvenanceResult


class C2PAService:
    """
    Stage 2 C2PA / Content Credentials Inspection Service.
    
    Responsibilities:
      - Inspects media files for embedded or remote C2PA provenance manifests.
      - Verifies cryptographic signature validity and signer certificate trust.
      - Never equates absence of C2PA with manipulation.
      - Never treats C2PA as a standalone deepfake detector or verdict.
      - Gracefully handles missing manifests, corrupt manifests, or parsing errors
        without crashing the overall analysis pipeline.
    """

    def __init__(self, trusted_signers: Optional[List[str]] = None):
        self.trusted_signers = trusted_signers or settings.TRUSTED_C2PA_SIGNERS

    def inspect(self, media_path: Path) -> ProvenanceResult:
        """
        Inspects the media file for C2PA manifests.
        
        Args:
            media_path: Local filesystem path to the uploaded video.
            
        Returns:
            ProvenanceResult detailing presence, signature validity, and signer trust.
        """
        if not media_path.exists() or media_path.stat().st_size == 0:
            return ProvenanceResult(
                state="UNAVAILABLE",
                valid=None,
                trusted=None,
                signer=None,
                note="Media file unavailable for provenance inspection."
            )

        try:
            import c2pa
        except ImportError:
            logger.warning("c2pa module is not installed. Returning UNAVAILABLE provenance state.")
            return ProvenanceResult(
                state="UNAVAILABLE",
                valid=None,
                trusted=None,
                signer=None,
                note="C2PA verification runtime library is not available in current environment."
            )

        try:
            reader = c2pa.Reader.try_create(format_or_path=str(media_path.resolve()))
            
            if reader is None:
                # No C2PA manifest found in container
                logger.info(f"C2PA inspection for {media_path.name}: No credentials found.")
                return ProvenanceResult(
                    state="NONE_FOUND",
                    valid=None,
                    trusted=None,
                    signer=None,
                    note="Absence of content credentials does not indicate manipulation."
                )

            # Manifest was found: extract manifest store and signature details
            manifest_json_str = reader.json()
            manifest_data = json.loads(manifest_json_str) if manifest_json_str else {}

            # Validation state
            validation_state = reader.get_validation_state()
            validation_str = str(validation_state).lower() if validation_state is not None else ""
            is_valid = bool(validation_state is not None and "valid" in validation_str and "invalid" not in validation_str)
            
            # Extract signer and assertion info
            signer_name = None
            ai_generated = False
            manifests = manifest_data.get("manifests", {})
            active_manifest_label = manifest_data.get("active_manifest")
            
            if active_manifest_label and active_manifest_label in manifests:
                active_manifest = manifests[active_manifest_label]
                sig_info = active_manifest.get("signature_info", {})
                signer_name = sig_info.get("issuer") or sig_info.get("cert_serial_number") or sig_info.get("time")

                # Check assertions for AI generation metadata
                assertions = active_manifest.get("assertions", [])
                for assertion in assertions:
                    label = str(assertion.get("label", "")).lower()
                    data = assertion.get("data", {})
                    data_str = json.dumps(data).lower() if isinstance(data, (dict, list)) else str(data).lower()
                    if any(term in data_str for term in [
                        "trainedalgorithmicmedia",
                        "compositesynthetic",
                        "algorithmicmedia",
                        "c2pa.synthetic",
                        "c2pa.ai_generated",
                    ]):
                        ai_generated = True
                        break
                    if "ai_generated" in label or "synthetic" in label:
                        ai_generated = True
                        break
                    if "c2pa.actions" in label and any(kw in data_str for kw in ["trainedalgorithmicmedia", "synthetic", "generative"]):
                        ai_generated = True
                        break

            # Check if signer is on configured trust list (only valid signatures can be trusted)
            is_trusted = False
            if is_valid and signer_name:
                for trusted in self.trusted_signers:
                    if trusted.lower() in signer_name.lower():
                        is_trusted = True
                        break

            # Construct informative explanatory note
            if ai_generated:
                if is_valid and is_trusted:
                    note = f"Content credentials verified from trusted signer '{signer_name}', explicitly declaring AI/algorithmic media generation."
                elif is_valid:
                    note = f"Content credentials verified from signer '{signer_name or 'Unknown'}', explicitly declaring AI/algorithmic media generation."
                else:
                    note = "Content credentials declare AI/algorithmic media generation, but cryptographic signature validation failed."
            elif is_valid and is_trusted:
                note = f"Content credentials were found with a valid cryptographic signature from trusted signer: '{signer_name}'."
            elif is_valid and not is_trusted:
                note = (
                    f"Content credentials were found and the signature is valid, but the signer "
                    f"('{signer_name or 'Unknown'}') is not on the configured trust list."
                )
            else:
                note = "Content credentials were found, but cryptographic signature validation failed or was untrusted."

            logger.info(
                f"C2PA inspection for {media_path.name}: state=FOUND | valid={is_valid} | "
                f"trusted={is_trusted} | signer={signer_name} | ai_generated={ai_generated}"
            )

            return ProvenanceResult(
                state="FOUND",
                valid=is_valid,
                trusted=is_trusted,
                signer=signer_name,
                ai_generated=ai_generated,
                note=note
            )

        except Exception as e:
            logger.warning(f"C2PA inspection failed on {media_path.name}: {e}. Analysis continuing.")
            return ProvenanceResult(
                state="ERROR",
                valid=None,
                trusted=None,
                signer=None,
                note=f"Unable to read content credentials from media container: {str(e)}"
            )
