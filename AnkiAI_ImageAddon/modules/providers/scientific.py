"""Scientific and specialty image providers (10 sources)."""

import json
import logging
import re
import time
import urllib.parse
from typing import Dict, List, Optional

from .base import ImageProviderError, _ImageProviderSessionManager, result_dict

logger = logging.getLogger(__name__)

SCIENTIFIC_PRECISE_PROVIDERS = {
    "pubchem",
    "chembl",
    "rcsb",
    "phylopic",
    "isic",
    "europe_pmc",
    "bioicons",
    "codecogs",
    "wikimedia_smart",
}


class PubChemProvider:
    """PubChem PUG-REST - molecular structure images."""

    def __init__(self):
        self.name = "pubchem"
        self.session = _ImageProviderSessionManager.get_session("pubchem")
        self._last_request = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < 0.25:
            time.sleep(0.25 - elapsed)
        self._last_request = time.time()

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        term = keyword.strip()
        try:
            self._rate_limit()
            encoded = urllib.parse.quote(term, safe="")
            cid_resp = self.session.get(
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/cids/JSON",
                timeout=6,
            )
            if cid_resp.status_code != 200:
                raise ImageProviderError(f"PubChem CID lookup {cid_resp.status_code}")
            cids = cid_resp.json().get("IdentifierList", {}).get("CID", [])
            if not cids:
                raise ImageProviderError("No compound found")
            images = []
            for cid in cids[:per_page]:
                url = (
                    f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/"
                    f"PNG?image_size=large"
                )
                images.append(result_dict(url, f"{term} (CID {cid})", self.name))
            return images
        except ImageProviderError:
            raise
        except Exception as e:
            raise ImageProviderError(str(e))


class ChEMBLProvider:
    """ChEMBL REST API - molecule depictions."""

    def __init__(self):
        self.name = "chembl"
        self.session = _ImageProviderSessionManager.get_session("chembl")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            response = self.session.get(
                "https://www.ebi.ac.uk/chembl/api/data/molecule/search",
                params={"q": keyword, "limit": per_page, "format": "json"},
                headers={"Accept": "application/json"},
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"ChEMBL {response.status_code}")
            molecules = response.json().get("molecules", [])
            if not molecules:
                raise ImageProviderError("No results")
            images = []
            for mol in molecules[:per_page]:
                chembl_id = mol.get("molecule_chembl_id")
                if not chembl_id:
                    continue
                url = (
                    f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}/"
                    f"image?format=svg&dimensions=500"
                )
                pref_name = mol.get("pref_name", keyword)
                images.append(result_dict(url, pref_name, self.name))
            if not images:
                raise ImageProviderError("No molecule images")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class RCSBProvider:
    """RCSB PDB search API - structure images."""

    def __init__(self):
        self.name = "rcsb"
        self.session = _ImageProviderSessionManager.get_session("rcsb")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            query = {
                "query": {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {"value": keyword},
                },
                "return_type": "entry",
                "request_options": {"paginate": {"start": 0, "rows": per_page}},
            }
            response = self.session.post(
                "https://search.rcsb.org/rcsbsearch/v2/query",
                json=query,
                headers={"Content-Type": "application/json"},
                timeout=8,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"RCSB {response.status_code}")
            ids = [r["identifier"] for r in response.json().get("result_set", [])]
            if not ids:
                raise ImageProviderError("No structures found")
            images = []
            for pdb_id in ids[:per_page]:
                url = f"https://cdn.rcsb.org/images/structures/{pdb_id.lower()}_assembly-1.jpeg"
                images.append(result_dict(url, f"PDB {pdb_id}", self.name))
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class PhyloPicProvider:
    """PhyloPic - silhouette images for taxonomy."""

    def __init__(self):
        self.name = "phylopic"
        self.session = _ImageProviderSessionManager.get_session("phylopic")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            response = self.session.get(
                "https://api.phylopic.org/images",
                params={
                    "filter_generic_name": keyword,
                    "embed_primaryImage": "true",
                    "items_per_page": per_page,
                },
                headers={"Accept": "application/json"},
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"PhyloPic {response.status_code}")
            items = response.json().get("items", [])
            if not items:
                raise ImageProviderError("No results")
            images = []
            for item in items[:per_page]:
                primary = item.get("_embedded", {}).get("primaryImage", {})
                url = primary.get("self") or primary.get("href")
                if not url and primary.get("@id"):
                    url = primary["@id"]
                if url:
                    images.append(
                        result_dict(url, item.get("genericName", keyword), self.name)
                    )
            if not images:
                raise ImageProviderError("No PhyloPic image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class ISICProvider:
    """ISIC Archive - dermatology images."""

    def __init__(self):
        self.name = "isic"
        self.session = _ImageProviderSessionManager.get_session("isic")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            response = self.session.get(
                "https://api.isic-archive.com/api/v2/image",
                params={
                    "name": keyword,
                    "limit": per_page,
                    "sort": "name",
                    "sortdir": 1,
                },
                timeout=8,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"ISIC {response.status_code}")
            results = response.json().get("results", [])
            if not results:
                raise ImageProviderError("No results")
            images = []
            for item in results[:per_page]:
                url = item.get("url_public") or item.get("url")
                if url:
                    name = item.get("name", keyword)
                    images.append(result_dict(url, name, self.name))
            if not images:
                raise ImageProviderError("No ISIC image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class EuropePMCProvider:
    """Europe PMC - disabled until figure URLs are validated (thumbnail API 404s)."""

    def __init__(self):
        self.name = "europe_pmc"
        self.session = _ImageProviderSessionManager.get_session("europe_pmc")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        # Runtime evidence: /thumbnail/1 URLs return HTTP 404 for PMC IDs.
        raise ImageProviderError("Europe PMC figure URLs unavailable")


class NASAImagesProvider:
    """NASA Image and Video Library."""

    def __init__(self):
        self.name = "nasa"
        self.session = _ImageProviderSessionManager.get_session("nasa")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://images-api.nasa.gov/search",
                params={"q": keyword, "media_type": "image"},
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"NASA {response.status_code}")
            items = response.json().get("collection", {}).get("items", [])
            if not items:
                raise ImageProviderError("No results")
            images = []
            for item in items[:per_page]:
                links = item.get("links", [])
                if links:
                    images.append(
                        result_dict(
                            links[0].get("href"),
                            item.get("data", [{}])[0].get("title", keyword),
                            self.name,
                        )
                    )
            if not images:
                raise ImageProviderError("No NASA image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class CodeCogsProvider:
    """CodeCogs LaTeX - renders formulas to SVG."""

    LATEX_PATTERN = re.compile(r"[\\^_{}]|\bfrac\b|\bsqrt\b|\bsum\b|\bint\b")

    def __init__(self):
        self.name = "codecogs"

    def search(self, keyword: str, per_page: int = 1) -> List[Dict]:
        if not self.LATEX_PATTERN.search(keyword):
            raise ImageProviderError("Not a LaTeX expression")
        try:
            encoded = urllib.parse.quote(keyword.strip(), safe="")
            url = f"https://latex.codecogs.com/svg.image?{encoded}"
            return [result_dict(url, keyword, self.name)]
        except Exception as e:
            raise ImageProviderError(str(e))


class BioiconsProvider:
    """Bioicons - biology SVG icons via GitHub manifest."""

    MANIFEST_URL = (
        "https://raw.githubusercontent.com/duerrfk/bioicons/main/icon_index.json"
    )

    def __init__(self):
        self.name = "bioicons"
        self.session = _ImageProviderSessionManager.get_session("bioicons")
        self._index: Optional[List[Dict]] = None

    def _load_index(self) -> List[Dict]:
        if self._index is not None:
            return self._index
        try:
            response = self.session.get(self.MANIFEST_URL, timeout=8)
            if response.status_code == 200:
                data = response.json()
                self._index = data if isinstance(data, list) else data.get("icons", [])
            else:
                self._index = []
        except Exception:
            self._index = []
        return self._index

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            index = self._load_index()
            if not index:
                raise ImageProviderError("Bioicons index unavailable")
            kw = keyword.lower()
            matches = []
            for entry in index:
                name = (
                    entry.get("name")
                    or entry.get("filename")
                    or entry.get("id", "")
                ).lower()
                tags = " ".join(entry.get("tags", [])).lower()
                if kw in name or kw in tags or any(w in name for w in kw.split()):
                    path = entry.get("path") or entry.get("file") or name
                    if not path.endswith(".svg"):
                        path = f"{path}.svg" if "." not in path else path
                    url = (
                        f"https://raw.githubusercontent.com/duerrfk/bioicons/main/{path}"
                    )
                    matches.append(result_dict(url, name, self.name))
                    if len(matches) >= per_page:
                        break
            if not matches:
                raise ImageProviderError("No bioicons match")
            return matches
        except ImageProviderError:
            raise
        except Exception as e:
            raise ImageProviderError(str(e))
