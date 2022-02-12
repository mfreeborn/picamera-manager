from flask_sqlalchemy import BaseQuery
from flask_sqlalchemy import Model as BaseModel


class Model(BaseModel):
    @classmethod
    def get(cls, ident):
        """Shorthand helper method for Query.get(id)"""
        return cls.query.get(ident)


class Query(BaseQuery):
    def scalars(self):
        """Akin to .scalar(), except it can be used on multiple rows."""
        try:
            return [x for x, in self]
        except ValueError as e:
            raise ValueError("Multiple values were found in a single result row.") from e
