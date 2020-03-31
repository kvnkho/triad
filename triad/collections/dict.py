import copy
import json
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from triad.utils.assertion import assert_arg_not_none
from triad.utils.convert import as_type
from triad.utils.iter import to_kv_iterable


class IndexedOrderedDict(OrderedDict):
    """Subclass of OrderedDict that can get and set with index
    """

    def __init__(self, *args: List[Any], **kwds: Dict[str, Any]):
        super().__init__(*args, **kwds)
        self._need_reindex = True
        self._key_index: Dict[Any, int] = {}
        self._index_key: List[Any] = []

    def index_of_key(self, key: Any) -> int:
        """Get index of key

        :param key: key value
        :return: index of the key value
        """
        self._build_index()
        return self._key_index[key]

    def get_key_by_index(self, index: int) -> Any:
        """Get key by index

        :param index: index of the key
        :return: key value at the index
        """
        self._build_index()
        return self._index_key[index]

    def get_value_by_index(self, index: int) -> Any:
        """Get value by index

        :param index: index of the item
        :return: value at the index
        """
        key = self.get_key_by_index(index)
        return self[key]

    def get_item_by_index(self, index: int) -> Tuple[Any, Any]:
        """Get key value pair by index

        :param index: index of the item
        :return: key value tuple at the index
        """
        key = self.get_key_by_index(index)
        return key, self[key]

    def set_value_by_index(self, index: int, value: Any) -> None:
        """Set value by index

        :param index: index of the item
        :param value: new value
        """
        key = self.get_key_by_index(index)
        self[key] = value

    def pop_by_index(self, index: int) -> Tuple[Any, Any]:
        """Pop item at index

        :param index: index of the item
        :return: key value tuple at the index
        """
        key = self.get_key_by_index(index)
        return key, self.pop(key)

    def equals(self, other: Any, with_order: bool):
        """Compare with another object

        :param other: for possible types, see :func:"~triad.utils.iter.to_kv_iterable"
        :param with_order: whether to compare order
        :return: whether they equal
        """
        if with_order:
            if isinstance(other, OrderedDict):
                return self == other
            return self == OrderedDict(to_kv_iterable(other))
        else:
            if isinstance(other, OrderedDict) or not isinstance(other, Dict):
                return self == dict(to_kv_iterable(other))
            return self == other

    # ----------------------------------- Wrappers over OrderedDict

    def __setitem__(  # type: ignore
        self, key: Any, value: Any, *args: List[Any], **kwds: Dict[str, Any]
    ) -> None:
        self._need_reindex = key not in self
        super().__setitem__(key, value, *args, **kwds)  # type: ignore

    def __delitem__(  # type: ignore
        self, *args: List[Any], **kwds: Dict[str, Any]
    ) -> None:
        self._need_reindex = True
        super().__delitem__(*args, **kwds)  # type: ignore

    def clear(self) -> None:
        self._need_reindex = True
        super().clear()

    def copy(self) -> "IndexedOrderedDict":
        other = super().copy()
        assert isinstance(other, IndexedOrderedDict)
        other._need_reindex = self._need_reindex
        other._index_key = self._index_key.copy()
        other._key_index = self._key_index.copy()
        return other

    def popitem(  # type: ignore
        self, *args: List[Any], **kwds: Dict[str, Any]
    ) -> Tuple[Any, Any]:
        self._need_reindex = True
        return super().popitem(*args, **kwds)  # type: ignore

    def move_to_end(  # type: ignore
        self, *args: List[Any], **kwds: Dict[str, Any]
    ) -> None:
        self._need_reindex = True
        super().move_to_end(*args, **kwds)  # type: ignore

    def __sizeof__(self) -> int:  # pragma: no cover
        return super().__sizeof__() + sys.getsizeof(self._need_reindex)

    def pop(  # type: ignore
        self, *args: List[Any], **kwds: Dict[str, Any]
    ) -> Any:
        self._need_reindex = True
        return super().pop(*args, **kwds)  # type: ignore

    def _build_index(self) -> None:
        if self._need_reindex:
            self._index_key = list(self.keys())
            self._key_index = {x: i for i, x in enumerate(self._index_key)}
            self._need_reindex = False


class ParamDict(IndexedOrderedDict):
    """Parameter dictionary, a subclass of `IndexedOrderedDict`, keys must be string

    :param data: for possible types, see :func:"~triad.utils.iter.to_kv_iterable"
    """

    OVERWRITE = 0
    THROW = 1
    IGNORE = 2

    def __init__(self, data: Any = None, deep: bool = True):
        super().__init__()
        self.update(data, deep=deep)

    def __setitem__(  # type: ignore
        self, key: Any, value: Any, *args: List[Any], **kwds: Dict[str, Any]
    ) -> None:
        assert isinstance(key, str)
        super().__setitem__(key, value, *args, **kwds)  # type: ignore

    def get(self, key: str, default: Any) -> Any:  # type: ignore
        """Get value by `key`, and the value must be a subtype of the type of `default`
        (which can't be None). If the `key` is not found, return `default`.

        :param key: the key to search
        :raises NoneArgumentError: if default is None
        :raises TypeError: if the value can't be converted to the type of `default`

        :return: the value by `key`, and the value must be a subtype of the type of
        `default`. If `key` is not found, return `default`
        """
        assert_arg_not_none(default, "default")
        if key in self:
            return as_type(self[key], type(default))
        return default

    def get_or_none(self, key: str, expected_type: type) -> Any:
        """Get value by `key`, and the value must be a subtype of `expected_type`

        :param key: the key to search
        :param expected_type: expected return value type

        :raises TypeError: if the value can't be converted to`expected_type`

        :return: if `key` is not found, None. Otherwise if the value can be converted
            to `expected_type`, return the converted value, otherwise raise exception
        """
        return self._get_or(key, expected_type, throw=False)

    def get_or_throw(self, key: str, expected_type: type) -> Any:
        """Get value by `key`, and the value must be a subtype of `expected_type`.
        If `key` is not found or value can't be converted to `expected_type`, raise
        exception

        :param key: the key to search
        :param expected_type: expected return value type

        :raises KeyError: if `key` is not found
        :raises TypeError: if the value can't be converted to `expected_type`

        :return: only when `key` is found and can be converted to `expected_type`,
            return the converted value
        """
        return self._get_or(key, expected_type, throw=True)

    def to_json_str(self, indent: bool = False) -> str:
        """Generate json expression string for the dictionary

        :param indent: whether to have indent
        :return: json string
        """
        if not indent:
            return json.dumps(self, separators=(",", ":"))
        else:
            return json.dumps(self, indent=4)

    def update(  # type: ignore
        self, other: Any, on_dup: int = 0, deep: bool = True
    ) -> "ParamDict":
        """Update dictionary with another object (for possible types,
        see :func:"~triad.utils.iter.to_kv_iterable")

        :param other: for possible types, see :func:"~triad.utils.iter.to_kv_iterable"
        :param on_dup: one of `ParamDict.OVERWRITE`, `ParamDict.THROW`
            and `ParamDict.IGNORE`

        :raises KeyError: if using `ParamDict.THROW` and other contains existing keys
        :raises ValueError: if `on_dup` is invalid
        :return: itself
        """
        for k, v in to_kv_iterable(other):
            if on_dup == ParamDict.OVERWRITE or k not in self:
                self[k] = copy.deepcopy(v) if deep else v
            elif on_dup == ParamDict.THROW:
                raise KeyError(f"{k} exists in dict")
            elif on_dup == ParamDict.IGNORE:
                continue
            else:
                raise ValueError(f"{on_dup} is not supported")
        return self

    def _get_or(self, key: str, expected_type: type, throw: bool = True) -> Any:
        if key in self:
            return as_type(self[key], expected_type)
        if throw:
            raise KeyError(f"{key} not found")
        return None