"""品类目录树单测：防 4 位章标题编码回归（曾导致全树不可用）。"""
import re

from luopan.config import CATEGORY_TREE


def test_all_codes_are_six_digit():
    for big, subs in CATEGORY_TREE.items():
        for item in subs:
            assert re.fullmatch(r"\d{6}", item["hs6"]), \
                "编码必须是 6 位数字: {}/{} -> {}".format(big, item["name"], item["hs6"])


def test_names_unique_within_major():
    for big, subs in CATEGORY_TREE.items():
        names = [x["name"] for x in subs]
        assert len(names) == len(set(names)), big + " 内细分名称重复"


def test_tree_structure_complete():
    assert len(CATEGORY_TREE) >= 10  # 大类规模
    for big, subs in CATEGORY_TREE.items():
        assert len(subs) >= 1, big + " 无细分"
        for item in subs:
            assert item["name"] and item["hs6"]


def test_no_exact_duplicate_entry_across_tree():
    seen = set()
    for big, subs in CATEGORY_TREE.items():
        for item in subs:
            key = (item["name"], item["hs6"])
            assert key not in seen, key
            seen.add(key)
