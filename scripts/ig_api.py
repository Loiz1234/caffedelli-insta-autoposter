"""
Wrapper do Instagram Graph API para publicacao automatica.
Docs: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
"""
import os
import time
import requests

GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


class IGError(Exception):
    pass


class InstagramPoster:
    def __init__(self, user_id: str, access_token: str):
        if not user_id or not access_token:
            raise IGError("IG_USER_ID e IG_ACCESS_TOKEN devem estar definidos")
        self.user_id = user_id
        self.access_token = access_token

    def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{BASE_URL}/{endpoint}"
        params = kwargs.pop("params", {})
        params["access_token"] = self.access_token
        r = requests.request(method, url, params=params, timeout=60, **kwargs)
        if r.status_code >= 400:
            raise IGError(f"IG API {r.status_code} em {endpoint}: {r.text[:500]}")
        return r.json()

    # ---------------- Containers ----------------
    def create_image_container(self, image_url: str, caption: str = "", is_carousel_item: bool = False) -> str:
        data = {"image_url": image_url}
        if caption:
            data["caption"] = caption
        if is_carousel_item:
            data["is_carousel_item"] = "true"
        r = self._request("POST", f"{self.user_id}/media", data=data)
        return r["id"]

    def create_video_container(self, video_url: str, caption: str = "", media_type: str = "REELS") -> str:
        data = {"video_url": video_url, "media_type": media_type}
        if caption:
            data["caption"] = caption
        r = self._request("POST", f"{self.user_id}/media", data=data)
        return r["id"]

    def create_carousel_container(self, children_ids: list, caption: str) -> str:
        data = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
        }
        r = self._request("POST", f"{self.user_id}/media", data=data)
        return r["id"]

    # ---------------- Status polling (video/reel) ----------------
    def wait_container_ready(self, container_id: str, timeout_s: int = 600, interval_s: int = 8) -> None:
        start = time.time()
        while time.time() - start < timeout_s:
            r = self._request("GET", container_id, params={"fields": "status_code"})
            status = r.get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise IGError(f"Container {container_id} falhou: status={status}")
            time.sleep(interval_s)
        raise IGError(f"Container {container_id} nao ficou pronto em {timeout_s}s")

    # ---------------- Publish ----------------
    def publish(self, container_id: str) -> dict:
        r = self._request("POST", f"{self.user_id}/media_publish", data={"creation_id": container_id})
        return r  # {"id": "<media_id>"}

    def get_permalink(self, media_id: str) -> str:
        try:
            r = self._request("GET", media_id, params={"fields": "permalink"})
            return r.get("permalink", "")
        except Exception:
            return ""

    # ---------------- High-level post methods ----------------
    def post_single_image(self, image_url: str, caption: str) -> dict:
        container = self.create_image_container(image_url, caption=caption)
        # Imagens publicam rapido, mas damos um pequeno buffer
        time.sleep(3)
        result = self.publish(container)
        result["permalink"] = self.get_permalink(result["id"])
        return result

    def post_carousel(self, image_urls: list, caption: str) -> dict:
        if len(image_urls) < 2 or len(image_urls) > 10:
            raise IGError(f"Carrossel exige 2 a 10 itens, recebido: {len(image_urls)}")
        children = [self.create_image_container(u, is_carousel_item=True) for u in image_urls]
        # Aguarda todos ficarem prontos
        for cid in children:
            self.wait_container_ready(cid, timeout_s=300)
        parent = self.create_carousel_container(children, caption)
        self.wait_container_ready(parent, timeout_s=300)
        result = self.publish(parent)
        result["permalink"] = self.get_permalink(result["id"])
        return result

    def post_reel(self, video_url: str, caption: str, cover_url: str = None) -> dict:
        data = {"video_url": video_url, "media_type": "REELS", "caption": caption}
        if cover_url:
            data["cover_url"] = cover_url
        r = self._request("POST", f"{self.user_id}/media", data=data)
        container = r["id"]
        self.wait_container_ready(container, timeout_s=900)  # video precisa processar
        result = self.publish(container)
        result["permalink"] = self.get_permalink(result["id"])
        return result
