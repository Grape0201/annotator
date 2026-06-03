from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Margin(BaseModel):
    top: int = Field(50, ge=0)
    bottom: int = Field(50, ge=0)
    left: int = Field(50, ge=0)
    right: int = Field(180, ge=0)

    model_config = ConfigDict(extra='forbid')


class Settings(BaseModel):
    page_size: Literal['A4', 'LETTER'] = 'A4'
    orientation: Literal['portrait', 'landscape'] = 'portrait'
    font_size: float = Field(9, gt=0)
    line_spacing: float = Field(1.3, gt=0)
    margin: Margin = Field(default_factory=lambda: Margin())  # type: ignore[assignment]
    show_line_numbers: bool = True
    show_filename: bool = True
    show_page_numbers: bool = True

    model_config = ConfigDict(extra='forbid')

    @field_validator('page_size', mode='before')
    @classmethod
    def normalize_page_size(cls, value):
        if value is None:
            return value
        return str(value).upper()

    @field_validator('orientation', mode='before')
    @classmethod
    def normalize_orientation(cls, value):
        if value is None:
            return value
        return str(value).lower()


class Annotation(BaseModel):
    line: int = Field(..., gt=0)
    col_start: int = Field(1, gt=0)
    col_end: int = Field(1, gt=0)
    type: Literal['text', 'highlight']
    position: Literal['margin', 'inline'] = 'margin'
    content: str = ''
    color: str = '#FFD700'
    opacity: float = Field(0.4, ge=0.0, le=1.0)
    bg_color: str = '#FFF5F5'

    model_config = ConfigDict(extra='forbid')

    @field_validator('position', mode='before')
    @classmethod
    def normalize_position(cls, value):
        if value is None:
            return value
        return str(value).lower()

    @model_validator(mode='after')
    def validate_annotation(self):
        if self.col_end < self.col_start:
            raise ValueError('col_end must be greater than or equal to col_start')

        if self.type == 'text' and not self.content:
            raise ValueError('content is required for text annotations')

        return self


class RenderConfig(BaseModel):
    settings: Settings = Field(default_factory=lambda: Settings())  # type: ignore[assignment]
    annotations: list[Annotation] = Field(default_factory=list)

    model_config = ConfigDict(extra='forbid')

    @field_validator('settings', mode='before')
    @classmethod
    def normalize_settings(cls, value):
        return {} if value is None else value

    @field_validator('annotations', mode='before')
    @classmethod
    def normalize_annotations(cls, value):
        return [] if value is None else value


def validate_config(data: dict | None) -> RenderConfig:
    if data is None:
        data = {}
    return RenderConfig.model_validate(data)
