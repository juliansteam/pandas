from collections import OrderedDict
import contextlib
from datetime import datetime, time
from functools import partial
import os
import warnings

import numpy as np
import pytest

import pandas.util._test_decorators as td

import pandas as pd
from pandas import DataFrame, Index, MultiIndex, Series
import pandas.util.testing as tm

from pandas.io.common import URLError
from pandas.io.excel import ExcelFile


@contextlib.contextmanager
def ignore_xlrd_time_clock_warning():
    """
    Context manager to ignore warnings raised by the xlrd library,
    regarding the deprecation of `time.clock` in Python 3.7.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            action='ignore',
            message='time.clock has been deprecated',
            category=DeprecationWarning)
        yield


class TestReaders:

    @pytest.fixture(autouse=True, params=[
        # Add any engines to test here
        pytest.param('xlrd', marks=pytest.mark.skipif(
            not td.safe_import("xlrd"), reason="no xlrd")),
        pytest.param(None, marks=pytest.mark.skipif(
            not td.safe_import("xlrd"), reason="no xlrd")),
    ])
    def cd_and_set_engine(self, request, datapath, monkeypatch):
        """
        Change directory and set engine for read_excel calls.
        """
        func = partial(pd.read_excel, engine=request.param)
        monkeypatch.chdir(datapath("io", "data"))
        monkeypatch.setattr(pd, 'read_excel', func)

    def test_usecols_int(self, read_ext, df_ref):
        df_ref = df_ref.reindex(columns=["A", "B", "C"])

        # usecols as int
        with tm.assert_produces_warning(FutureWarning,
                                        check_stacklevel=False):
            with ignore_xlrd_time_clock_warning():
                df1 = pd.read_excel("test1" + read_ext, "Sheet1",
                                    index_col=0, usecols=3)

        # usecols as int
        with tm.assert_produces_warning(FutureWarning,
                                        check_stacklevel=False):
            with ignore_xlrd_time_clock_warning():
                df2 = pd.read_excel("test1" + read_ext, "Sheet2", skiprows=[1],
                                    index_col=0, usecols=3)

        # TODO add index to xls file)
        tm.assert_frame_equal(df1, df_ref, check_names=False)
        tm.assert_frame_equal(df2, df_ref, check_names=False)

    def test_usecols_list(self, read_ext, df_ref):

        df_ref = df_ref.reindex(columns=['B', 'C'])
        df1 = pd.read_excel('test1' + read_ext, 'Sheet1', index_col=0,
                            usecols=[0, 2, 3])
        df2 = pd.read_excel('test1' + read_ext, 'Sheet2', skiprows=[1],
                            index_col=0, usecols=[0, 2, 3])

        # TODO add index to xls file)
        tm.assert_frame_equal(df1, df_ref, check_names=False)
        tm.assert_frame_equal(df2, df_ref, check_names=False)

    def test_usecols_str(self, read_ext, df_ref):

        df1 = df_ref.reindex(columns=['A', 'B', 'C'])
        df2 = pd.read_excel('test1' + read_ext, 'Sheet1', index_col=0,
                            usecols='A:D')
        df3 = pd.read_excel('test1' + read_ext, 'Sheet2', skiprows=[1],
                            index_col=0, usecols='A:D')

        # TODO add index to xls, read xls ignores index name ?
        tm.assert_frame_equal(df2, df1, check_names=False)
        tm.assert_frame_equal(df3, df1, check_names=False)

        df1 = df_ref.reindex(columns=['B', 'C'])
        df2 = pd.read_excel('test1' + read_ext, 'Sheet1', index_col=0,
                            usecols='A,C,D')
        df3 = pd.read_excel('test1' + read_ext, 'Sheet2', skiprows=[1],
                            index_col=0, usecols='A,C,D')
        # TODO add index to xls file
        tm.assert_frame_equal(df2, df1, check_names=False)
        tm.assert_frame_equal(df3, df1, check_names=False)

        df1 = df_ref.reindex(columns=['B', 'C'])
        df2 = pd.read_excel('test1' + read_ext, 'Sheet1', index_col=0,
                            usecols='A,C:D')
        df3 = pd.read_excel('test1' + read_ext, 'Sheet2', skiprows=[1],
                            index_col=0, usecols='A,C:D')
        tm.assert_frame_equal(df2, df1, check_names=False)
        tm.assert_frame_equal(df3, df1, check_names=False)

    @pytest.mark.parametrize("usecols", [
        [0, 1, 3], [0, 3, 1],
        [1, 0, 3], [1, 3, 0],
        [3, 0, 1], [3, 1, 0],
    ])
    def test_usecols_diff_positional_int_columns_order(
            self, read_ext, usecols, df_ref):
        expected = df_ref[["A", "C"]]
        result = pd.read_excel("test1" + read_ext, "Sheet1",
                               index_col=0, usecols=usecols)
        tm.assert_frame_equal(result, expected, check_names=False)

    @pytest.mark.parametrize("usecols", [
        ["B", "D"], ["D", "B"]
    ])
    def test_usecols_diff_positional_str_columns_order(
            self, read_ext, usecols, df_ref):
        expected = df_ref[["B", "D"]]
        expected.index = range(len(expected))

        result = pd.read_excel("test1" + read_ext, "Sheet1", usecols=usecols)
        tm.assert_frame_equal(result, expected, check_names=False)

    def test_read_excel_without_slicing(self, read_ext, df_ref):
        expected = df_ref
        result = pd.read_excel("test1" + read_ext, "Sheet1", index_col=0)
        tm.assert_frame_equal(result, expected, check_names=False)

    def test_usecols_excel_range_str(self, read_ext, df_ref):
        expected = df_ref[["C", "D"]]
        result = pd.read_excel("test1" + read_ext, "Sheet1",
                               index_col=0, usecols="A,D:E")
        tm.assert_frame_equal(result, expected, check_names=False)

    def test_usecols_excel_range_str_invalid(self, read_ext):
        msg = "Invalid column name: E1"

        with pytest.raises(ValueError, match=msg):
            pd.read_excel("test1" + read_ext, "Sheet1", usecols="D:E1")

    def test_index_col_label_error(self, read_ext):
        msg = "list indices must be integers.*, not str"

        with pytest.raises(TypeError, match=msg):
            pd.read_excel("test1" + read_ext, "Sheet1", index_col=["A"],
                          usecols=["A", "C"])

    def test_index_col_empty(self, read_ext):
        # see gh-9208
        result = pd.read_excel("test1" + read_ext, "Sheet3",
                               index_col=["A", "B", "C"])
        expected = DataFrame(columns=["D", "E", "F"],
                             index=MultiIndex(levels=[[]] * 3,
                                              codes=[[]] * 3,
                                              names=["A", "B", "C"]))
        tm.assert_frame_equal(result, expected)

    @pytest.mark.parametrize("index_col", [None, 2])
    def test_index_col_with_unnamed(self, read_ext, index_col):
        # see gh-18792
        result = pd.read_excel(
            "test1" + read_ext, "Sheet4", index_col=index_col)
        expected = DataFrame([["i1", "a", "x"], ["i2", "b", "y"]],
                             columns=["Unnamed: 0", "col1", "col2"])
        if index_col:
            expected = expected.set_index(expected.columns[index_col])

        tm.assert_frame_equal(result, expected)

    def test_usecols_pass_non_existent_column(self, read_ext):
        msg = ("Usecols do not match columns, "
               "columns expected but not found: " + r"\['E'\]")

        with pytest.raises(ValueError, match=msg):
            pd.read_excel("test1" + read_ext, usecols=["E"])

    def test_usecols_wrong_type(self, read_ext):
        msg = ("'usecols' must either be list-like of "
               "all strings, all unicode, all integers or a callable.")

        with pytest.raises(ValueError, match=msg):
            pd.read_excel("test1" + read_ext, usecols=["E1", 0])

    def test_excel_stop_iterator(self, read_ext):

        parsed = pd.read_excel('test2' + read_ext, 'Sheet1')
        expected = DataFrame([['aaaa', 'bbbbb']], columns=['Test', 'Test1'])
        tm.assert_frame_equal(parsed, expected)

    def test_excel_cell_error_na(self, read_ext):

        parsed = pd.read_excel('test3' + read_ext, 'Sheet1')
        expected = DataFrame([[np.nan]], columns=['Test'])
        tm.assert_frame_equal(parsed, expected)

    def test_excel_table(self, read_ext, df_ref):

        df1 = pd.read_excel('test1' + read_ext, 'Sheet1', index_col=0)
        df2 = pd.read_excel('test1' + read_ext, 'Sheet2', skiprows=[1],
                            index_col=0)
        # TODO add index to file
        tm.assert_frame_equal(df1, df_ref, check_names=False)
        tm.assert_frame_equal(df2, df_ref, check_names=False)

        df3 = pd.read_excel(
            'test1' + read_ext, 'Sheet1', index_col=0, skipfooter=1)
        tm.assert_frame_equal(df3, df1.iloc[:-1])

    def test_reader_special_dtypes(self, read_ext):

        expected = DataFrame.from_dict(OrderedDict([
            ("IntCol", [1, 2, -3, 4, 0]),
            ("FloatCol", [1.25, 2.25, 1.83, 1.92, 0.0000000005]),
            ("BoolCol", [True, False, True, True, False]),
            ("StrCol", [1, 2, 3, 4, 5]),
            # GH5394 - this is why convert_float isn't vectorized
            ("Str2Col", ["a", 3, "c", "d", "e"]),
            ("DateCol", [datetime(2013, 10, 30), datetime(2013, 10, 31),
                         datetime(1905, 1, 1), datetime(2013, 12, 14),
                         datetime(2015, 3, 14)])
        ]))
        basename = 'test_types'

        # should read in correctly and infer types
        actual = pd.read_excel(basename + read_ext, 'Sheet1')
        tm.assert_frame_equal(actual, expected)

        # if not coercing number, then int comes in as float
        float_expected = expected.copy()
        float_expected["IntCol"] = float_expected["IntCol"].astype(float)
        float_expected.loc[float_expected.index[1], "Str2Col"] = 3.0
        actual = pd.read_excel(
            basename + read_ext, 'Sheet1', convert_float=False)
        tm.assert_frame_equal(actual, float_expected)

        # check setting Index (assuming xls and xlsx are the same here)
        for icol, name in enumerate(expected.columns):
            actual = pd.read_excel(
                basename + read_ext, 'Sheet1', index_col=icol)
            exp = expected.set_index(name)
            tm.assert_frame_equal(actual, exp)

        # convert_float and converters should be different but both accepted
        expected["StrCol"] = expected["StrCol"].apply(str)
        actual = pd.read_excel(basename + read_ext, 'Sheet1',
                               converters={"StrCol": str})
        tm.assert_frame_equal(actual, expected)

        no_convert_float = float_expected.copy()
        no_convert_float["StrCol"] = no_convert_float["StrCol"].apply(str)
        actual = pd.read_excel(
            basename + read_ext, 'Sheet1',
            convert_float=False, converters={"StrCol": str})
        tm.assert_frame_equal(actual, no_convert_float)

    # GH8212 - support for converters and missing values
    def test_reader_converters(self, read_ext):

        basename = 'test_converters'

        expected = DataFrame.from_dict(OrderedDict([
            ("IntCol", [1, 2, -3, -1000, 0]),
            ("FloatCol", [12.5, np.nan, 18.3, 19.2, 0.000000005]),
            ("BoolCol", ['Found', 'Found', 'Found', 'Not found', 'Found']),
            ("StrCol", ['1', np.nan, '3', '4', '5']),
        ]))

        converters = {'IntCol': lambda x: int(x) if x != '' else -1000,
                      'FloatCol': lambda x: 10 * x if x else np.nan,
                      2: lambda x: 'Found' if x != '' else 'Not found',
                      3: lambda x: str(x) if x else '',
                      }

        # should read in correctly and set types of single cells (not array
        # dtypes)
        actual = pd.read_excel(
            basename + read_ext, 'Sheet1', converters=converters)
        tm.assert_frame_equal(actual, expected)

    def test_reader_dtype(self, read_ext):
        # GH 8212
        basename = 'testdtype'
        actual = pd.read_excel(basename + read_ext)

        expected = DataFrame({
            'a': [1, 2, 3, 4],
            'b': [2.5, 3.5, 4.5, 5.5],
            'c': [1, 2, 3, 4],
            'd': [1.0, 2.0, np.nan, 4.0]}).reindex(
                columns=['a', 'b', 'c', 'd'])

        tm.assert_frame_equal(actual, expected)

        actual = pd.read_excel(basename + read_ext,
                               dtype={'a': 'float64',
                                      'b': 'float32',
                                      'c': str})

        expected['a'] = expected['a'].astype('float64')
        expected['b'] = expected['b'].astype('float32')
        expected['c'] = ['001', '002', '003', '004']
        tm.assert_frame_equal(actual, expected)

        with pytest.raises(ValueError):
            pd.read_excel(basename + read_ext, dtype={'d': 'int64'})

    @pytest.mark.parametrize("dtype,expected", [
        (None,
         DataFrame({
             "a": [1, 2, 3, 4],
             "b": [2.5, 3.5, 4.5, 5.5],
             "c": [1, 2, 3, 4],
             "d": [1.0, 2.0, np.nan, 4.0]
         })),
        ({"a": "float64",
          "b": "float32",
          "c": str,
          "d": str
          },
         DataFrame({
             "a": Series([1, 2, 3, 4], dtype="float64"),
             "b": Series([2.5, 3.5, 4.5, 5.5], dtype="float32"),
             "c": ["001", "002", "003", "004"],
             "d": ["1", "2", np.nan, "4"]
         })),
    ])
    def test_reader_dtype_str(self, read_ext, dtype, expected):
        # see gh-20377
        basename = "testdtype"

        actual = pd.read_excel(basename + read_ext, dtype=dtype)
        tm.assert_frame_equal(actual, expected)

    def test_reading_all_sheets(self, read_ext):
        # Test reading all sheetnames by setting sheetname to None,
        # Ensure a dict is returned.
        # See PR #9450
        basename = 'test_multisheet'
        dfs = pd.read_excel(basename + read_ext, sheet_name=None)
        # ensure this is not alphabetical to test order preservation
        expected_keys = ['Charlie', 'Alpha', 'Beta']
        tm.assert_contains_all(expected_keys, dfs.keys())
        # Issue 9930
        # Ensure sheet order is preserved
        assert expected_keys == list(dfs.keys())

    def test_reading_multiple_specific_sheets(self, read_ext):
        # Test reading specific sheetnames by specifying a mixed list
        # of integers and strings, and confirm that duplicated sheet
        # references (positions/names) are removed properly.
        # Ensure a dict is returned
        # See PR #9450
        basename = 'test_multisheet'
        # Explicitly request duplicates. Only the set should be returned.
        expected_keys = [2, 'Charlie', 'Charlie']
        dfs = pd.read_excel(basename + read_ext, sheet_name=expected_keys)
        expected_keys = list(set(expected_keys))
        tm.assert_contains_all(expected_keys, dfs.keys())
        assert len(expected_keys) == len(dfs.keys())

    def test_reading_all_sheets_with_blank(self, read_ext):
        # Test reading all sheetnames by setting sheetname to None,
        # In the case where some sheets are blank.
        # Issue #11711
        basename = 'blank_with_header'
        dfs = pd.read_excel(basename + read_ext, sheet_name=None)
        expected_keys = ['Sheet1', 'Sheet2', 'Sheet3']
        tm.assert_contains_all(expected_keys, dfs.keys())

    # GH6403
    def test_read_excel_blank(self, read_ext):
        actual = pd.read_excel('blank' + read_ext, 'Sheet1')
        tm.assert_frame_equal(actual, DataFrame())

    def test_read_excel_blank_with_header(self, read_ext):
        expected = DataFrame(columns=['col_1', 'col_2'])
        actual = pd.read_excel('blank_with_header' + read_ext, 'Sheet1')
        tm.assert_frame_equal(actual, expected)

    def test_date_conversion_overflow(self, read_ext):
        # GH 10001 : pandas.ExcelFile ignore parse_dates=False
        expected = pd.DataFrame([[pd.Timestamp('2016-03-12'), 'Marc Johnson'],
                                 [pd.Timestamp('2016-03-16'), 'Jack Black'],
                                 [1e+20, 'Timothy Brown']],
                                columns=['DateColWithBigInt', 'StringCol'])

        result = pd.read_excel('testdateoverflow' + read_ext)
        tm.assert_frame_equal(result, expected)

    def test_sheet_name(self, read_ext, df_ref):
        filename = "test1"
        sheet_name = "Sheet1"

        df1 = pd.read_excel(filename + read_ext,
                            sheet_name=sheet_name, index_col=0)  # doc
        with ignore_xlrd_time_clock_warning():
            df2 = pd.read_excel(filename + read_ext, index_col=0,
                                sheet_name=sheet_name)

        tm.assert_frame_equal(df1, df_ref, check_names=False)
        tm.assert_frame_equal(df2, df_ref, check_names=False)

    def test_excel_read_buffer(self, read_ext):

        pth = 'test1' + read_ext
        expected = pd.read_excel(pth, 'Sheet1', index_col=0)
        with open(pth, 'rb') as f:
            actual = pd.read_excel(f, 'Sheet1', index_col=0)
            tm.assert_frame_equal(expected, actual)

    def test_bad_engine_raises(self, read_ext):
        bad_engine = 'foo'
        with pytest.raises(ValueError, match="Unknown engine: foo"):
            pd.read_excel('', engine=bad_engine)

    @tm.network
    def test_read_from_http_url(self, read_ext):
        url = ('https://raw.github.com/pandas-dev/pandas/master/'
               'pandas/tests/io/data/test1' + read_ext)
        url_table = pd.read_excel(url)
        local_table = pd.read_excel('test1' + read_ext)
        tm.assert_frame_equal(url_table, local_table)

    @td.skip_if_not_us_locale
    def test_read_from_s3_url(self, read_ext, s3_resource):
        # Bucket "pandas-test" created in tests/io/conftest.py
        with open('test1' + read_ext, "rb") as f:
            s3_resource.Bucket("pandas-test").put_object(
                Key="test1" + read_ext, Body=f)

        url = ('s3://pandas-test/test1' + read_ext)
        url_table = pd.read_excel(url)
        local_table = pd.read_excel('test1' + read_ext)
        tm.assert_frame_equal(url_table, local_table)

    @pytest.mark.slow
    # ignore warning from old xlrd
    @pytest.mark.filterwarnings("ignore:This metho:PendingDeprecationWarning")
    def test_read_from_file_url(self, read_ext, datapath):

        # FILE
        localtable = os.path.join(datapath("io", "data"), 'test1' + read_ext)
        local_table = pd.read_excel(localtable)

        try:
            url_table = pd.read_excel('file://localhost/' + localtable)
        except URLError:
            # fails on some systems
            import platform
            pytest.skip("failing on %s" %
                        ' '.join(platform.uname()).strip())

        tm.assert_frame_equal(url_table, local_table)

    def test_read_from_pathlib_path(self, read_ext):

        # GH12655
        from pathlib import Path

        str_path = 'test1' + read_ext
        expected = pd.read_excel(str_path, 'Sheet1', index_col=0)

        path_obj = Path('test1' + read_ext)
        actual = pd.read_excel(path_obj, 'Sheet1', index_col=0)

        tm.assert_frame_equal(expected, actual)

    @td.skip_if_no('py.path')
    def test_read_from_py_localpath(self, read_ext):

        # GH12655
        from py.path import local as LocalPath

        str_path = os.path.join('test1' + read_ext)
        expected = pd.read_excel(str_path, 'Sheet1', index_col=0)

        path_obj = LocalPath().join('test1' + read_ext)
        actual = pd.read_excel(path_obj, 'Sheet1', index_col=0)

        tm.assert_frame_equal(expected, actual)

    def test_reader_seconds(self, read_ext):

        # Test reading times with and without milliseconds. GH5945.
        expected = DataFrame.from_dict({"Time": [time(1, 2, 3),
                                                 time(2, 45, 56, 100000),
                                                 time(4, 29, 49, 200000),
                                                 time(6, 13, 42, 300000),
                                                 time(7, 57, 35, 400000),
                                                 time(9, 41, 28, 500000),
                                                 time(11, 25, 21, 600000),
                                                 time(13, 9, 14, 700000),
                                                 time(14, 53, 7, 800000),
                                                 time(16, 37, 0, 900000),
                                                 time(18, 20, 54)]})

        actual = pd.read_excel('times_1900' + read_ext, 'Sheet1')
        tm.assert_frame_equal(actual, expected)

        actual = pd.read_excel('times_1904' + read_ext, 'Sheet1')
        tm.assert_frame_equal(actual, expected)

    def test_read_excel_multiindex(self, read_ext):
        # see gh-4679
        mi = MultiIndex.from_product([["foo", "bar"], ["a", "b"]])
        mi_file = "testmultiindex" + read_ext

        # "mi_column" sheet
        expected = DataFrame([[1, 2.5, pd.Timestamp("2015-01-01"), True],
                              [2, 3.5, pd.Timestamp("2015-01-02"), False],
                              [3, 4.5, pd.Timestamp("2015-01-03"), False],
                              [4, 5.5, pd.Timestamp("2015-01-04"), True]],
                             columns=mi)

        actual = pd.read_excel(
            mi_file, "mi_column", header=[0, 1], index_col=0)
        tm.assert_frame_equal(actual, expected)

        # "mi_index" sheet
        expected.index = mi
        expected.columns = ["a", "b", "c", "d"]

        actual = pd.read_excel(mi_file, "mi_index", index_col=[0, 1])
        tm.assert_frame_equal(actual, expected, check_names=False)

        # "both" sheet
        expected.columns = mi

        actual = pd.read_excel(
            mi_file, "both", index_col=[0, 1], header=[0, 1])
        tm.assert_frame_equal(actual, expected, check_names=False)

        # "mi_index_name" sheet
        expected.columns = ["a", "b", "c", "d"]
        expected.index = mi.set_names(["ilvl1", "ilvl2"])

        actual = pd.read_excel(
            mi_file, "mi_index_name", index_col=[0, 1])
        tm.assert_frame_equal(actual, expected)

        # "mi_column_name" sheet
        expected.index = list(range(4))
        expected.columns = mi.set_names(["c1", "c2"])
        actual = pd.read_excel(mi_file, "mi_column_name",
                               header=[0, 1], index_col=0)
        tm.assert_frame_equal(actual, expected)

        # see gh-11317
        # "name_with_int" sheet
        expected.columns = mi.set_levels(
            [1, 2], level=1).set_names(["c1", "c2"])

        actual = pd.read_excel(mi_file, "name_with_int",
                               index_col=0, header=[0, 1])
        tm.assert_frame_equal(actual, expected)

        # "both_name" sheet
        expected.columns = mi.set_names(["c1", "c2"])
        expected.index = mi.set_names(["ilvl1", "ilvl2"])

        actual = pd.read_excel(mi_file, "both_name",
                               index_col=[0, 1], header=[0, 1])
        tm.assert_frame_equal(actual, expected)

        # "both_skiprows" sheet
        actual = pd.read_excel(mi_file, "both_name_skiprows", index_col=[0, 1],
                               header=[0, 1], skiprows=2)
        tm.assert_frame_equal(actual, expected)

    def test_read_excel_multiindex_header_only(self, read_ext):
        # see gh-11733.
        #
        # Don't try to parse a header name if there isn't one.
        mi_file = "testmultiindex" + read_ext
        result = pd.read_excel(mi_file, "index_col_none", header=[0, 1])

        exp_columns = MultiIndex.from_product([("A", "B"), ("key", "val")])
        expected = DataFrame([[1, 2, 3, 4]] * 2, columns=exp_columns)
        tm.assert_frame_equal(result, expected)

    def test_excel_old_index_format(self, read_ext):
        # see gh-4679
        filename = "test_index_name_pre17" + read_ext

        # We detect headers to determine if index names exist, so
        # that "index" name in the "names" version of the data will
        # now be interpreted as rows that include null data.
        data = np.array([[None, None, None, None, None],
                         ["R0C0", "R0C1", "R0C2", "R0C3", "R0C4"],
                         ["R1C0", "R1C1", "R1C2", "R1C3", "R1C4"],
                         ["R2C0", "R2C1", "R2C2", "R2C3", "R2C4"],
                         ["R3C0", "R3C1", "R3C2", "R3C3", "R3C4"],
                         ["R4C0", "R4C1", "R4C2", "R4C3", "R4C4"]])
        columns = ["C_l0_g0", "C_l0_g1", "C_l0_g2", "C_l0_g3", "C_l0_g4"]
        mi = MultiIndex(levels=[["R0", "R_l0_g0", "R_l0_g1",
                                 "R_l0_g2", "R_l0_g3", "R_l0_g4"],
                                ["R1", "R_l1_g0", "R_l1_g1",
                                 "R_l1_g2", "R_l1_g3", "R_l1_g4"]],
                        codes=[[0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4, 5]],
                        names=[None, None])
        si = Index(["R0", "R_l0_g0", "R_l0_g1", "R_l0_g2",
                    "R_l0_g3", "R_l0_g4"], name=None)

        expected = pd.DataFrame(data, index=si, columns=columns)

        actual = pd.read_excel(filename, "single_names", index_col=0)
        tm.assert_frame_equal(actual, expected)

        expected.index = mi

        actual = pd.read_excel(filename, "multi_names", index_col=[0, 1])
        tm.assert_frame_equal(actual, expected)

        # The analogous versions of the "names" version data
        # where there are explicitly no names for the indices.
        data = np.array([["R0C0", "R0C1", "R0C2", "R0C3", "R0C4"],
                         ["R1C0", "R1C1", "R1C2", "R1C3", "R1C4"],
                         ["R2C0", "R2C1", "R2C2", "R2C3", "R2C4"],
                         ["R3C0", "R3C1", "R3C2", "R3C3", "R3C4"],
                         ["R4C0", "R4C1", "R4C2", "R4C3", "R4C4"]])
        columns = ["C_l0_g0", "C_l0_g1", "C_l0_g2", "C_l0_g3", "C_l0_g4"]
        mi = MultiIndex(levels=[["R_l0_g0", "R_l0_g1", "R_l0_g2",
                                 "R_l0_g3", "R_l0_g4"],
                                ["R_l1_g0", "R_l1_g1", "R_l1_g2",
                                 "R_l1_g3", "R_l1_g4"]],
                        codes=[[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
                        names=[None, None])
        si = Index(["R_l0_g0", "R_l0_g1", "R_l0_g2",
                    "R_l0_g3", "R_l0_g4"], name=None)

        expected = pd.DataFrame(data, index=si, columns=columns)

        actual = pd.read_excel(filename, "single_no_names", index_col=0)
        tm.assert_frame_equal(actual, expected)

        expected.index = mi

        actual = pd.read_excel(filename, "multi_no_names", index_col=[0, 1])
        tm.assert_frame_equal(actual, expected, check_names=False)

    def test_read_excel_bool_header_arg(self, read_ext):
        # GH 6114
        for arg in [True, False]:
            with pytest.raises(TypeError):
                pd.read_excel('test1' + read_ext, header=arg)

    def test_read_excel_chunksize(self, read_ext):
        # GH 8011
        with pytest.raises(NotImplementedError):
            pd.read_excel('test1' + read_ext, chunksize=100)

    def test_read_excel_skiprows_list(self, read_ext):
        # GH 4903
        actual = pd.read_excel('testskiprows' + read_ext,
                               'skiprows_list', skiprows=[0, 2])
        expected = DataFrame([[1, 2.5, pd.Timestamp('2015-01-01'), True],
                              [2, 3.5, pd.Timestamp('2015-01-02'), False],
                              [3, 4.5, pd.Timestamp('2015-01-03'), False],
                              [4, 5.5, pd.Timestamp('2015-01-04'), True]],
                             columns=['a', 'b', 'c', 'd'])
        tm.assert_frame_equal(actual, expected)

        actual = pd.read_excel('testskiprows' + read_ext,
                               'skiprows_list', skiprows=np.array([0, 2]))
        tm.assert_frame_equal(actual, expected)

    def test_read_excel_nrows(self, read_ext):
        # GH 16645
        num_rows_to_pull = 5
        actual = pd.read_excel('test1' + read_ext, nrows=num_rows_to_pull)
        expected = pd.read_excel('test1' + read_ext)
        expected = expected[:num_rows_to_pull]
        tm.assert_frame_equal(actual, expected)

    def test_read_excel_nrows_greater_than_nrows_in_file(self, read_ext):
        # GH 16645
        expected = pd.read_excel('test1' + read_ext)
        num_records_in_file = len(expected)
        num_rows_to_pull = num_records_in_file + 10
        actual = pd.read_excel('test1' + read_ext, nrows=num_rows_to_pull)
        tm.assert_frame_equal(actual, expected)

    def test_read_excel_nrows_non_integer_parameter(self, read_ext):
        # GH 16645
        msg = "'nrows' must be an integer >=0"
        with pytest.raises(ValueError, match=msg):
            pd.read_excel('test1' + read_ext, nrows='5')

    def test_read_excel_squeeze(self, read_ext):
        # GH 12157
        f = 'test_squeeze' + read_ext

        actual = pd.read_excel(f, 'two_columns', index_col=0, squeeze=True)
        expected = pd.Series([2, 3, 4], [4, 5, 6], name='b')
        expected.index.name = 'a'
        tm.assert_series_equal(actual, expected)

        actual = pd.read_excel(f, 'two_columns', squeeze=True)
        expected = pd.DataFrame({'a': [4, 5, 6],
                                 'b': [2, 3, 4]})
        tm.assert_frame_equal(actual, expected)

        actual = pd.read_excel(f, 'one_column', squeeze=True)
        expected = pd.Series([1, 2, 3], name='a')
        tm.assert_series_equal(actual, expected)


class TestExcelFileRead:

    @pytest.fixture(autouse=True, params=[
        # Add any engines to test here
        pytest.param('xlrd', marks=pytest.mark.skipif(
            not td.safe_import("xlrd"), reason="no xlrd")),
        pytest.param(None, marks=pytest.mark.skipif(
            not td.safe_import("xlrd"), reason="no xlrd")),
    ])
    def cd_and_set_engine(self, request, datapath, monkeypatch):
        """
        Change directory and set engine for ExcelFile objects.
        """
        func = partial(pd.ExcelFile, engine=request.param)
        monkeypatch.chdir(datapath("io", "data"))
        monkeypatch.setattr(pd, 'ExcelFile', func)

    def test_excel_passes_na(self, read_ext):

        excel = ExcelFile('test4' + read_ext)

        parsed = pd.read_excel(excel, 'Sheet1', keep_default_na=False,
                               na_values=['apple'])
        expected = DataFrame([['NA'], [1], ['NA'], [np.nan], ['rabbit']],
                             columns=['Test'])
        tm.assert_frame_equal(parsed, expected)

        parsed = pd.read_excel(excel, 'Sheet1', keep_default_na=True,
                               na_values=['apple'])
        expected = DataFrame([[np.nan], [1], [np.nan], [np.nan], ['rabbit']],
                             columns=['Test'])
        tm.assert_frame_equal(parsed, expected)

        # 13967
        excel = ExcelFile('test5' + read_ext)

        parsed = pd.read_excel(excel, 'Sheet1', keep_default_na=False,
                               na_values=['apple'])
        expected = DataFrame([['1.#QNAN'], [1], ['nan'], [np.nan], ['rabbit']],
                             columns=['Test'])
        tm.assert_frame_equal(parsed, expected)

        parsed = pd.read_excel(excel, 'Sheet1', keep_default_na=True,
                               na_values=['apple'])
        expected = DataFrame([[np.nan], [1], [np.nan], [np.nan], ['rabbit']],
                             columns=['Test'])
        tm.assert_frame_equal(parsed, expected)

    @pytest.mark.parametrize('arg', ['sheet', 'sheetname', 'parse_cols'])
    def test_unexpected_kwargs_raises(self, read_ext, arg):
        # gh-17964
        excel = ExcelFile('test1' + read_ext)

        kwarg = {arg: 'Sheet1'}
        msg = "unexpected keyword argument `{}`".format(arg)
        with pytest.raises(TypeError, match=msg):
            pd.read_excel(excel, **kwarg)

    def test_excel_table_sheet_by_index(self, read_ext, df_ref):

        excel = ExcelFile('test1' + read_ext)

        df1 = pd.read_excel(excel, 0, index_col=0)
        df2 = pd.read_excel(excel, 1, skiprows=[1], index_col=0)
        tm.assert_frame_equal(df1, df_ref, check_names=False)
        tm.assert_frame_equal(df2, df_ref, check_names=False)

        df1 = excel.parse(0, index_col=0)
        df2 = excel.parse(1, skiprows=[1], index_col=0)
        tm.assert_frame_equal(df1, df_ref, check_names=False)
        tm.assert_frame_equal(df2, df_ref, check_names=False)

        df3 = pd.read_excel(excel, 0, index_col=0, skipfooter=1)
        tm.assert_frame_equal(df3, df1.iloc[:-1])

        with tm.assert_produces_warning(FutureWarning, check_stacklevel=False):
            df4 = pd.read_excel(excel, 0, index_col=0, skip_footer=1)
            tm.assert_frame_equal(df3, df4)

        df3 = excel.parse(0, index_col=0, skipfooter=1)
        tm.assert_frame_equal(df3, df1.iloc[:-1])

        import xlrd  # will move to engine-specific tests as new ones are added
        with pytest.raises(xlrd.XLRDError):
            pd.read_excel(excel, 'asdf')

    def test_sheet_name(self, read_ext, df_ref):
        filename = "test1"
        sheet_name = "Sheet1"

        excel = ExcelFile(filename + read_ext)
        df1_parse = excel.parse(sheet_name=sheet_name, index_col=0)  # doc
        df2_parse = excel.parse(index_col=0,
                                sheet_name=sheet_name)

        tm.assert_frame_equal(df1_parse, df_ref, check_names=False)
        tm.assert_frame_equal(df2_parse, df_ref, check_names=False)

    def test_excel_read_buffer(self, read_ext):

        pth = 'test1' + read_ext
        expected = pd.read_excel(pth, 'Sheet1', index_col=0)

        with open(pth, 'rb') as f:
            xls = ExcelFile(f)
            actual = pd.read_excel(xls, 'Sheet1', index_col=0)
            tm.assert_frame_equal(expected, actual)

    def test_reader_closes_file(self, read_ext):

        f = open('test1' + read_ext, 'rb')
        with ExcelFile(f) as xlsx:
            # parses okay
            pd.read_excel(xlsx, 'Sheet1', index_col=0)

        assert f.closed
