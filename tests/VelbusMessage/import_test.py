def test_import_all():
    i = __import__('velbus.VelbusMessage', fromlist=['*'])
    assert i.ModuleTypeRequest
    assert i.ModuleInfo.UnknownModuleInfo
