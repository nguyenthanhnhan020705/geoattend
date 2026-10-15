from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator


class PolygonInput(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    type: Literal['Polygon']
    coordinates: list[list[list[float]]] = Field(min_length=1,max_length=10)

    @model_validator(mode='after')
    def validate_rings(self):
        if sum(len(ring) for ring in self.coordinates)>2000:
            raise ValueError('Too many vertices')
        for ring in self.coordinates:
            if not 4<=len(ring)<=1001 or ring[0]!=ring[-1]:
                raise ValueError('Closed ring required')
            for point in ring:
                if len(point)!=2 or not -180<=point[0]<=180 or not -90<=point[1]<=90:
                    raise ValueError('Invalid longitude/latitude')
        return self


class OfficeInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name: str = Field(min_length=1,max_length=200)
    address: str = Field(min_length=1,max_length=1000)
    geom: PolygonInput
    expected_revision: int = Field(ge=0,strict=True)

    @model_validator(mode='after')
    def trim_text(self):
        self.name=self.name.strip(); self.address=self.address.strip()
        if not self.name or not self.address:
            raise ValueError('Name and address required')
        return self
