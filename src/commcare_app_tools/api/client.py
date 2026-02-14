"""Base API client with pagination support."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

from ..auth.session import AuthenticatedClient
from ..config.environments import ConfigManager


class CommCareAPI:
    """High-level client for the CommCare HQ API.

    Wraps AuthenticatedClient with convenience methods for common
    API patterns like pagination and domain-scoped requests.

    Usage:
        config = ConfigManager()
        api = CommCareAPI(config, domain="my-domain")
        cases = api.list("api/case/v2/")
        for page in api.paginate("api/case/v2/"):
            process(page)
    """

    def __init__(
        self,
        config: ConfigManager,
        domain: str | None = None,
        env_name: str | None = None,
    ):
        self.config = config
        self.domain = domain
        self.env_name = env_name
        self._client = AuthenticatedClient(config, env_name)

    def _build_path(self, path: str) -> str:
        """Build a full API path, prepending domain if needed.

        If the path already starts with /a/ or is absolute, use as-is.
        Otherwise, prepend /a/{domain}/.
        """
        path = path.lstrip("/")
        if path.startswith("a/") or path.startswith("api/global/"):
            return f"/{path}"
        if self.domain:
            return f"/a/{self.domain}/{path}"
        return f"/{path}"

    def get(self, path: str, params: dict | None = None, **kwargs: Any) -> httpx.Response:
        """Make a GET request to the API."""
        full_path = self._build_path(path)
        return self._client.get(full_path, params=params, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a POST request to the API."""
        full_path = self._build_path(path)
        return self._client.post(full_path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a PUT request to the API."""
        full_path = self._build_path(path)
        return self._client.put(full_path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a DELETE request to the API."""
        full_path = self._build_path(path)
        return self._client.delete(full_path, **kwargs)

    def list(
        self,
        path: str,
        params: dict | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict:
        """Fetch a single page of results from a list endpoint.

        Args:
            path: API path (e.g. "api/case/v2/").
            params: Additional query parameters.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            The JSON response as a dict.
        """
        request_params = dict(params or {})
        if limit is not None:
            request_params["limit"] = limit
        if offset:
            request_params["offset"] = offset

        response = self.get(path, params=request_params)
        response.raise_for_status()
        return response.json()

    def paginate(
        self,
        path: str,
        params: dict | None = None,
        page_size: int = 20,
        max_results: int | None = None,
    ) -> Iterator[list[dict]]:
        """Iterate over all pages of a paginated API endpoint.

        Yields lists of objects (one per page). Handles both
        Tastypie-style (meta.next) and DRF-style (next URL) pagination.

        Args:
            path: API path.
            params: Additional query parameters.
            page_size: Number of results per page.
            max_results: Stop after this many total results.
        """
        offset = 0
        total_fetched = 0

        while True:
            request_params = dict(params or {})
            request_params["limit"] = page_size
            request_params["offset"] = offset

            response = self.get(path, params=request_params)
            response.raise_for_status()
            data = response.json()

            # Handle Tastypie-style responses
            if "objects" in data:
                objects = data["objects"]
                has_next = bool(data.get("meta", {}).get("next"))
            # Handle DRF-style responses
            elif "results" in data:
                objects = data["results"]
                has_next = bool(data.get("next"))
            # Handle plain list responses
            elif isinstance(data, list):
                objects = data
                has_next = len(data) == page_size
            else:
                objects = [data]
                has_next = False

            if not objects:
                break

            yield objects

            total_fetched += len(objects)
            if max_results and total_fetched >= max_results:
                break
            if not has_next:
                break

            offset += page_size

    def get_user_info(self) -> dict:
        """Get information about the currently authenticated user.

        Uses the identity API endpoint (not domain-scoped).
        """
        response = self._client.get("/api/identity/v1/")
        response.raise_for_status()
        return response.json()

    def list_domains(self) -> list[dict]:
        """List all domains the authenticated user has access to.

        Uses the user_domains API endpoint (not domain-scoped).
        """
        response = self._client.get("/api/user_domains/v1/")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "objects" in data:
            return data["objects"]
        if isinstance(data, list):
            return data
        return [data]

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
