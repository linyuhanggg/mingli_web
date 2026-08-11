class ApiProblem(Exception):
    def __init__(
        self,
        *,
        status: int,
        title: str,
        problem_type: str = "about:blank",
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        clear_device_cookies: bool = False,
    ) -> None:
        super().__init__(title)
        self.status = status
        self.title = title
        self.problem_type = problem_type
        self.detail = detail
        self.headers = headers
        self.clear_device_cookies = clear_device_cookies
