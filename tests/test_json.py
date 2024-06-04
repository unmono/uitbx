import unittest
import os
from pathlib import Path

from uitbx.keepers.JSONAttributeKeeper import JSONAttributeKeeper


class TestClass:
    class_attr = 'string class attribute'

    def __init__(
            self,
            **kwargs
    ):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestJson(unittest.TestCase):
    def setUp(self):
        self.files = {
            'default_file_path': Path.cwd() / 'preferences.json',
            'custom_file_path': Path('tests') / 'prefs.json',
            'string_file_path': 'tests/prefs_string.json',
            'existed_file_path': Path('tests/prefs_existed.json'),
        }
        self.bad_file_path = 'directory_that_doesnt_exist/prefs_bad.json'
        self.not_permitted_file = Path('tests/prefs_not_permitted.json')
        self.not_permitted_file.touch()
        self.not_permitted_file.chmod(0o555)
        self.files['existed_file_path'].touch()

        self.serializable_values = {
            'str_attr': 'string',
            'int_attr': 1,
            'bool_attr': True,
            'float_attr': 1.1,
        }
        self.serializable_values_changed = {
            'str_attr': 'string_changed',
            'int_attr': 11,
            'bool_attr': False,
            'float_attr': 2.2,
        }
        self.serializable_values_object = TestClass(**self.serializable_values)

        self.convertable_values = {
            'path_value': Path.cwd()
        }
        self.convertable_values_changed = {
            'path_value': Path.cwd() / 'hi',
        }
        self.convertable_values_object = TestClass(**self.convertable_values)

    def tearDown(self):
        self.not_permitted_file.chmod(0o777)
        try:
            os.remove(self.not_permitted_file)
        except OSError:
            pass

        for p in self.files.values():
            try:
                os.remove(Path(p))
            except OSError:
                pass

    def test_serializable_values(self):
        self.workflow(
            self.serializable_values_object,
            self.serializable_values,
            self.serializable_values_changed,
        )

    def test_file_paths(self):
        self.assertRaises(
            FileNotFoundError,
            JSONAttributeKeeper,
            self.serializable_values_object,
            self.serializable_values,
            self.bad_file_path,
        )
        self.assertRaises(
            PermissionError,
            JSONAttributeKeeper,
            self.serializable_values_object,
            self.serializable_values,
            self.not_permitted_file,
        )
        for p in self.files.values():
            keeper = JSONAttributeKeeper(
                self.serializable_values_object,
                self.serializable_values,
                p,
            )
            self.assertEqual(Path(p), keeper.file)

    def test_converters(self):
        self.workflow(
            self.convertable_values_object,
            self.convertable_values,
            self.convertable_values_changed
        )

    def test_classvar(self):
        keeper = JSONAttributeKeeper(
            TestClass(),
            ['class_attr'],
        )
        keeper.save()
        old_value = keeper.obj.class_attr
        keeper.obj.class_attr = 'new value'
        keeper.setup()
        self.assertEqual(keeper.obj.class_attr, old_value)

    def workflow(self, obj, values, changed_values):
        keeper = JSONAttributeKeeper(
            obj,
            values.keys(),
        )
        keeper.save()
        for k, v in changed_values.items():
            setattr(obj, k, v)
        self.assertEqual(obj.__dict__, changed_values)
        keeper.setup()
        self.assertEqual(obj.__dict__, values)
