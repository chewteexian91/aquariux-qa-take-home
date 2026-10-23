from dataclasses import dataclass, field


@dataclass
class User:
    role: str
    username: str
    password: str = field(repr=False)
