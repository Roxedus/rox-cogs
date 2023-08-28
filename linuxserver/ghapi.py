from typing import Literal

import aiohttp

USER_TYPES = Literal["user", "orgs"]


class GitHubAPI:
    """
    GitHub API wrapper
    """

    def __init__(self, token: str) -> None:
        self.session: aiohttp.ClientSession
        self._token: str
        self._create_session(token)

    def _create_session(self, token: str) -> None:
        headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.shadow-cat-preview+json",
            "User-Agent": "Py aiohttp - redbot"
        }
        self._token = token
        self.session = aiohttp.ClientSession(headers=headers)

    async def get_repos(self, user_type: USER_TYPES, entity: str) -> list:
        """
        Get all repos for a user or org
        """
        url = f"https://api.github.com/{user_type}/{entity}/repos"

        async with self.session.get(url, timeout=10, params={"per_page": 100, "page": 1, "type": "public"}) as res:
            ghRepos = await res.json()
            if isinstance(ghRepos, dict):
                return []
            while "next" in res.links.keys():
                res = await self.session.get(res.links["next"]["url"], timeout=10)
                ghRepos.extend(await res.json())

        return ghRepos

    async def verify_repo(self, entity: str, repo: str) -> bool:
        """
        Verify if a repo exists for a user or org
        """
        url = f"https://api.github.com/repos/{entity}/{repo}"
        async with self.session.get(url, timeout=10) as res:
            if res.status == 404:
                return False
            return True
