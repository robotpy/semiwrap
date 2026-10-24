import inspect

from swtest import ft


def test_doc_code_block_in_return_with_parameter_rename():
    obj = ft.DocCodeBlocks()
    assert obj.example(value=4) == 5
    signature, body = inspect.getdoc(obj.example).split("\n\n", 1)
    assert "value:" in signature
    assert "\n".join(line.rstrip() for line in body.splitlines()) == inspect.cleandoc(
        r"""
        Compute the next value.

        :param value: Input value.

        :returns: Result value.

                  .. code-block:: python

                     if value:
                         result = item.example(value)

                         print("result:", result, "\\")
        """
    )


def test_doc_code_class_preserves_diagram_and_appends_rst():
    doc = inspect.getdoc(ft.DocCodeBlocks)
    assert doc == inspect.cleandoc(
        """
        A class with examples.

        ::

           +---+
           | x |
           +---+

        Create an instance:

        .. code-block:: python

           item = DocCodeBlocks()

        Additional notes.

        .. code-block:: cpp

           appended();
        """
    )


def test_doc_code_property():
    obj = ft.DocCodeBlocks()
    obj.value = 5
    assert obj.value == 5
    assert inspect.getdoc(ft.DocCodeBlocks.value) == inspect.cleandoc(
        """
        Set the value:

        .. code-block:: python

           item.value = 5
        """
    )


def test_doc_code_free_function_multiple_blocks():
    assert ft.doc_code_function() == 42
    body = inspect.getdoc(ft.doc_code_function).split("\n\n", 1)[1]
    assert body == inspect.cleandoc(
        """
        Function examples:

        .. code-block:: python

           x = doc_code_function()

        Another example:

        .. code-block:: python

           value = doc_code_function()
        """
    )


def test_doc_code_omitted_and_disabled():
    assert ft.doc_code_unchanged() == 1
    assert ft.doc_code_disabled() == 2
    for fn, source in [
        (ft.doc_code_unchanged, "auto x = doc_code_unchanged();"),
        (ft.doc_code_disabled, "auto x = doc_code_disabled();"),
    ]:
        body = inspect.getdoc(fn).split("\n\n", 1)[1]
        assert body == ".. code-block:: cpp\n\n   " + source


def test_doc_code_overload_inheritance_and_disabling():
    obj = ft.DocCodeBlocks()
    assert obj.overloaded(7) == 7
    assert obj.overloaded(1.5) == 1.5
    doc = inspect.getdoc(obj.overloaded)
    assert "item.overloaded(1);" not in doc
    assert "item.overloaded(1.5);" not in doc
    # One method-level example is inherited, another overload replaces it,
    # and the third disables it. Check actual combined pybind11 documentation.
    assert doc.count("integer_example()") == 1
    assert doc.count("inherited_example()") == 1
    assert doc.count("item.overloaded(true);") == 1
    assert doc.count(".. code-block:: python") == 2


def test_doc_code_overload_can_disable_replacements_with_full_doc():
    obj = ft.DocCodeBlocks()
    assert obj.overridden(5) == 5
    assert inspect.getdoc(obj.overridden).split("\n\n", 1)[1] == "Full override."


def test_doc_code_enum_and_value():
    doc = inspect.getdoc(ft.DocCodeEnum)
    assert "Enum examples." in doc
    assert "value = DocCodeEnum.Ready" in doc
    assert "enum_example = DocCodeEnum.Ready" in doc
    assert "DocCodeEnum::Ready" not in doc
    assert doc.count(".. code-block:: python") == 2
    assert ft.DocCodeEnum.Ready.value == 0


def test_doc_code_shared_template_examples():
    assert ft.DocCodeTemplateInt().echo(7) == 7
    assert ft.DocCodeTemplateDouble().echo(1.5) == 1.5
    first = inspect.getdoc(ft.DocCodeTemplateInt)
    assert first == inspect.getdoc(ft.DocCodeTemplateDouble)
    assert first == inspect.cleandoc(
        """
        Templated example.

        .. code-block:: python

           instance = DocCodeTemplateInt()
        """
    )


def test_docstrings_enum():
    assert inspect.getdoc(ft.DocEnum) == inspect.cleandoc(
        """
        An enum that is documented
        Maybe it's not great docs, but it's something.

        Members:

          Value1 : value 1 doc
        
          Value2 : value 2 doc??
        """
    )


def test_docstrings_cls():
    assert inspect.getdoc(ft.DocClass) == inspect.cleandoc(
        """
        A class with documentation
        The docs are way cool.
        """
    )


def test_docstrings_meth():
    assert inspect.getdoc(ft.DocClass.fn) == inspect.cleandoc(
        """
        fn(self: swtest.ft._ft.DocClass) -> None
        
        Function with docstring for good measure
        """
    )


def test_docstrings_meth_kwd():
    assert inspect.getdoc(ft.DocClass.fn2) == inspect.cleandoc(
        """
        fn2(self: swtest.ft._ft.DocClass, from_: typing.SupportsInt | typing.SupportsIndex) -> None
        
        Function with parameter that's a python keyword

        :param from_: The from parameter
        """
    )


def test_docstrings_meth_rename():
    assert inspect.getdoc(ft.DocClass.fn3) == inspect.cleandoc(
        """
        fn3(self: swtest.ft._ft.DocClass, ohai: typing.SupportsInt | typing.SupportsIndex) -> None
        
        Function with renamed parameter

        :param ohai: The renamed parameter
        """
    )


def test_docstrings_var():
    assert (
        inspect.getdoc(ft.DocClass.sweet_var)
        == "An awesome variable, use it for something"
    )


def test_docstrings_fn():
    assert inspect.getdoc(ft.important_retval) == inspect.cleandoc(
        """
        important_retval() -> int

        This function returns something very important
        """
    )


def test_docstrings_append():
    assert inspect.getdoc(ft.DocAppendEnum) == inspect.cleandoc(
        """
        An enum that is documented
        Maybe it's not great docs, but it's something.
        Useful extra information about this enum


        Members:

          Value1 : value 1 doc
          Useful extra information about this value
          
        
          Value2 : value 2 doc??
        """
    )

    assert inspect.getdoc(ft.DocAppendClass) == inspect.cleandoc(
        """
        A class with documentation
        The docs are way cool.
        Useful extra information about this sweet class
        """
    )
    assert inspect.getdoc(ft.DocAppendClass.fn) == inspect.cleandoc(
        """
        fn(self: swtest.ft._ft.DocAppendClass) -> None
        
        Function with docstring for good measure
        Useful extra information about this fn
        """
    )
    assert inspect.getdoc(ft.DocAppendClass.sweet_var) == inspect.cleandoc(
        """
        An awesome variable, use it for something
        Useful extra information about this sweet var
        """
    )


def test_docstrings_template():
    assert inspect.getdoc(ft.DocTemplateSet) == "Set docs to this"

    assert inspect.getdoc(ft.DocTemplateAppend) == inspect.cleandoc(
        """
        A templated class
        Extra appended docs
    """
    )
