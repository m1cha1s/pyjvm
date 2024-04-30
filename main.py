#!/usr/bin/env python3

import pprint
import struct


class JVMClassFile:
    def __init__(self, path: str) -> None:
        self.klassFile = open(path, "rb")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.klassFile.close()

    def U1(self):
        return struct.unpack_from(">B", self.klassFile.read(1))[0]
        
    def U2(self):
        return struct.unpack_from(">H", self.klassFile.read(2))[0]

    def U4(self):
        return struct.unpack_from(">I", self.klassFile.read(4))[0]

    def U(self, n: int):
        return struct.unpack_from(">"+"s"*n, self.klassFile.read(n))
        


class JVMConstant:
    CONSTANT_Class = 7
    CONSTANT_Fieldref = 9
    CONSTANT_Methodref = 10
    CONSTANT_InterfaceMethodref = 11
    CONSTANT_String = 8
    CONSTANT_Integer = 3
    CONSTANT_Float = 4
    CONSTANT_Long = 5
    CONSTANT_Double = 6
    CONSTANT_NameAndType = 12
    CONSTANT_Utf8 = 1
    CONSTANT_MethodHandle = 15
    CONSTANT_MethodType = 16
    CONSTANT_InvokeDynamic = 18

    def __init__(self, klassFile: JVMClassFile) -> None:
        self.tag = klassFile.U1()
        match self.tag:
            case self.CONSTANT_Class:
                self.name_index = klassFile.U2()
            case self.CONSTANT_Fieldref | self.CONSTANT_Methodref | self.CONSTANT_InterfaceMethodref:
                self.class_index = klassFile.U2()
                self.name_and_type_index = klassFile.U2()
            case self.CONSTANT_String:
                self.string_index = klassFile.U2() 
            case self.CONSTANT_Integer:
                self.bytes = klassFile.U4()
            case self.CONSTANT_Float: 
                self.bytes = klassFile.U4()
            case self.CONSTANT_Long | self.CONSTANT_Double:
                self.high_bytes = klassFile.U4()
                self.low_bytes = klassFile.U4()
            case self.CONSTANT_NameAndType:
                self.name_index = klassFile.U2()
                self.descriptor_index = klassFile.U2()
            case self.CONSTANT_Utf8: 
                self.length = klassFile.U2()
                self.bytes = (b''.join(klassFile.U(self.length))).decode('utf-8')
            case self.CONSTANT_MethodHandle:
                self.reference_kind = klassFile.U1()
                self.reference_index = klassFile.U2()
            case self.CONSTANT_MethodType:
                self.descriptor_index = klassFile.U2()
            case self.CONSTANT_InvokeDynamic:
                self.bootstrap_method_attr_index = klassFile.U2()
                self.name_and_type_index = klassFile.U2()

    def __str__(self) -> str:
        if self.tag == self.CONSTANT_Utf8:
            return self.bytes
        return f"-- UNKNOWN {self.tag} --"

   
    def __repr__(self) -> str:
        if self.tag == self.CONSTANT_Utf8:
            return self.bytes
        return f"-- UNKNOWN {self.tag} --"


class JVMCodeAttr:
    def __init__(self, klass) -> None:
        klassFile = klass.klassFile
        self.max_stack = klassFile.U2()
        self.max_locals = klassFile.U2()
        self.code_length = klassFile.U4()
        self.code = klassFile.U(self.code_length)

        self.exception_table_length = klassFile.U2()
        
        self.exception_table = [{'start_pc': klassFile.U2(), 
                                 'end_pc': klassFile.U2(),
                                 'handler_pc': klassFile.U2(),
                                 'catch_type': klassFile.U2()} for _ in range(self.exception_table_length)]

        self.attributes_count = klassFile.U2()
        self.attributes = [JVMAttribute(klass) for _ in range(self.attributes_count)]


class JVMAttribute:
    def __init__(self, klass) -> None:
        klassFile = klass.klassFile
        self.attribute_name_index = klassFile.U2()

        self.attribute_name = klass.constant_pool[self.attribute_name_index-1]
        self.attribute_length = klassFile.U4()

        if str(self.attribute_name) == "Code":
            self.info = JVMCodeAttr(klass)
        else:
            self.info = klassFile.U(self.attribute_length)

    def __repr__(self) -> str:
        return str(self.attribute_name)

    def __str__(self) -> str:
        return str(self.attribute_name)


class JVMMethod:
    def __init__(self, klass) -> None:
        klassFile = klass.klassFile
        self.access_flags = klassFile.U2()
        self.name_index = klassFile.U2()
        self.descriptor_index = klassFile.U2()
        self.attributes_count = klassFile.U2()
        self.attributes = [JVMAttribute(klass) for _ in range(self.attributes_count)]

class JVMField:
    def __init__(self, klass) -> None:
        klassFile = klass.klassFile
        self.access_flags = klassFile.U2()
        self.name_index = klassFile.U2()
        self.descriptor_index = klassFile.U2()
        self.attributes_count = klassFile.U2()
        self.attributes = [JVMAttribute(klass) for _ in range(self.attributes_count)]


class JVMClass:
    def __init__(self, path: str = "main.class"):
        with JVMClassFile(path) as self.klassFile:
            self.validate_class_file_magic()

            self.minor_version = self.klassFile.U2() 
            self.major_version = self.klassFile.U2()

            print(f"Class version: {self.major_version}.{self.minor_version}")

            self.read_constant_pool()

            self.access_flags = self.klassFile.U2()
            self.this_class = self.klassFile.U2()
            self.super_class = self.klassFile.U2()

            self.interfaces_count = self.klassFile.U2()
            self.interfaces = [self.klassFile.U2() for _ in range(self.interfaces_count)]

            self.fields_count = self.klassFile.U2()
            self.fields = [JVMField(self) for _ in range(self.fields_count)]

            self.methods_count = self.klassFile.U2()
            self.methods = [JVMMethod(self) for _ in range(self.methods_count)]

            self.attributes_count = self.klassFile.U2()
            self.attributes = [JVMAttribute(self) for _ in range(self.attributes_count)]

    def validate_class_file_magic(self):
        magic = self.klassFile.U4()
        if magic != 0xCAFEBABE:
            raise BaseException("Invalid class file")

    def read_constant_pool(self):
        self.constant_pool_count = self.klassFile.U2()

        self.constant_pool = [JVMConstant(self.klassFile) for _ in range(self.constant_pool_count-1)]
            

if __name__ == '__main__':
    kf = JVMClass()