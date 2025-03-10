from dataclasses import asdict, dataclass


@dataclass
class ActivityPubObject:
    id: str
    type: str

    @classmethod
    def from_json(cls, data):
        return cls(**data)

    def to_dict(self):
        return asdict(self)
