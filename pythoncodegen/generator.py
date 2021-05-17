from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import List, Tuple, Iterable


class PythonCodeGenerator(ABC):
    def __init__(self):
        self._indentation_character: str = ' '
        self._indentation_size: int = 4
        self._indentation_level: int = 0
        self._indentation_str: str = ''
        self._update_indentation_str()

    def __str__(self):
        return self._generate_str()

    @abstractmethod
    def _generate_str(self):
        pass

    @abstractmethod
    def empty(self):
        pass

    def _update_indentation_str(self):
        self._indentation_str = self._indentation_character * self._indentation_size

    def set_indentation_character(self, indentation_character: str):
        if len(indentation_character) != 1:
            raise ValueError('Indentation character length should be of length 1.')
        self._indentation_character = indentation_character
        self._update_indentation_str()

    def set_indentation_size(self, indentation_size: int):
        if indentation_size < 1:
            raise ValueError('Indentation size should be at least 1.')
        self._indentation_size = indentation_size
        self._update_indentation_str()

    def set_indentation_level(self, indentation_level: int):
        if indentation_level < 0:
            raise ValueError('Indentation level should be greater than 0.')
        self._indentation_level = indentation_level


def update_indentation(python_code_generators: Iterable[PythonCodeGenerator], indentation_level: int):
    for generator in python_code_generators:
        generator.set_indentation_level(indentation_level)


class PythonExpressionCodeGenerator(PythonCodeGenerator):
    def __init__(self, expression: str):
        super(PythonExpressionCodeGenerator, self).__init__()
        self._expression = expression

    def _generate_str(self):
        return f'{self._indentation_str * self._indentation_level}{self._expression}'

    def empty(self):
        return False


class PythonAssignmentCodeGenerator(PythonCodeGenerator):
    def __init__(self, name: str, value: str):
        super(PythonAssignmentCodeGenerator, self).__init__()
        self._name = name
        self._value = value

    def _generate_str(self):
        return f'{self._indentation_str * self._indentation_level}{self._name} = {self._value}\n'

    def empty(self):
        return False


class PythonFunctionCodeGenerator(PythonCodeGenerator):
    def __init__(self,
                 name: str,
                 params: Tuple[str, ...],
                 lines: Tuple[PythonCodeGenerator, ...],
                 decorators: Tuple[str, ...]):
        super(PythonFunctionCodeGenerator, self).__init__()
        self._name = name
        self._params = params
        self._lines = lines
        self._decorators = decorators
        self._class_method = False

    def _generate_signature(self):
        base_indentation = self._indentation_str * self._indentation_level
        decorators = list(self._decorators)
        params = ', '.join(self._params)
        if self._class_method:
            decorators += ([f'{base_indentation}@staticmethod'] if len(self._params) == 0 else [])
        decorators += ([''] if len(decorators) else [])
        decorators = '\n'.join(decorators)
        return f'{decorators}{base_indentation}def {self._name}({params}):\n'

    def _generate_line(self, line):
        indentation_level = self._indentation_level + 1
        line.set_indentation_level(indentation_level)
        return str(line)

    def _generate_body(self):
        if self.empty():
            return f'{self._indentation_str * (self._indentation_level + 1)}pass\n'
        lines = map(lambda line: f'{self._generate_line(line)}\n', self._lines)
        return ''.join(lines)

    def _generate_str(self):
        signature = self._generate_signature()
        body = self._generate_body()
        return f'{signature}{body}'

    def empty(self):
        return len(self._lines) == 0

    def set_class_method(self, class_method: bool):
        self._class_method = class_method

    def set_indentation_level(self, indentation_level: int):
        super(PythonFunctionCodeGenerator, self).set_indentation_level(indentation_level)
        for line in self._lines:
            if type(line) != str:
                line.set_indentation_level(self._indentation_level + 1)


class PythonClassCodeGenerator(PythonCodeGenerator):
    def __init__(self, name: str, super_classes: Tuple[str, ...]):
        super(PythonClassCodeGenerator, self).__init__()
        self._name = name
        self._super_classes = super_classes
        self._class_attributes: List[PythonAssignmentCodeGenerator] = []
        self._nested_class_generators: List[PythonClassCodeGenerator] = []
        self._method_generators: List[PythonFunctionCodeGenerator] = []

    def _generate_signature(self):
        base_indentation = self._indentation_str * self._indentation_level
        super_classes = f'({", ".join(self._super_classes)})' if len(self._super_classes) else ''
        return f'{base_indentation}class {self._name}{super_classes}:\n'

    def _generate_body(self):
        if self.empty():
            return f'{self._indentation_str * (self._indentation_level + 1)}pass\n'

        class_attributes = ''.join(map(lambda attribute: str(attribute), self._class_attributes))
        nested_classes = '\n'.join(map(lambda nested_class: str(nested_class), self._nested_class_generators))
        methods = '\n'.join(map(lambda method: str(method), self._method_generators))
        first_separator = '\n' if len(self._class_attributes) > 0 else ''
        second_separator = '\n' if len(self._nested_class_generators) > 0 else ''
        return f'{class_attributes}{first_separator}{nested_classes}{second_separator}{methods}'

    def _generate_str(self):
        signature = self._generate_signature()
        body = self._generate_body()
        return f'{signature}{body}'

    def empty(self):
        return len(self._class_attributes) == 0 and len(self._nested_class_generators) == 0 and \
               len(self._method_generators) == 0

    def add_class_attribute(self, assignment_code_generator: PythonAssignmentCodeGenerator):
        assignment_code_generator.set_indentation_level(self._indentation_level + 1)
        self._class_attributes.append(assignment_code_generator)

    def add_method(self, function_code_generator: PythonFunctionCodeGenerator):
        function_code_generator.set_class_method(True)
        function_code_generator.set_indentation_level(self._indentation_level + 1)
        self._method_generators.append(function_code_generator)

    def add_nested_class(self, class_code_generator: PythonClassCodeGenerator):
        class_code_generator.set_indentation_level(self._indentation_level + 1)
        self._nested_class_generators.append(class_code_generator)

    def set_indentation_level(self, indentation_level: int):
        super(PythonClassCodeGenerator, self).set_indentation_level(indentation_level)
        code_generator_iterables = [self._class_attributes, self._method_generators, self._nested_class_generators]
        for generator_iterable in code_generator_iterables:
            update_indentation(generator_iterable, self._indentation_level + 1)


class PythonModuleCodeGenerator(PythonCodeGenerator):
    def __init__(self, name, path):
        super(PythonModuleCodeGenerator, self).__init__()
        self._name = name
        self._path = path
        self._components: List[PythonCodeGenerator] = []

    def _generate_str(self):
        components = map(lambda component: str(component), self._components)
        module_code = '\n\n'.join(components)
        return f'\n\n{module_code}\n'

    def empty(self):
        return len(self._components) == 0

    def add_component(self, component: PythonCodeGenerator):
        self._components.append(component)

    def save(self):
        file_path = f'{self._path}/{self._name}.py'
        with open(file_path, 'w') as outfile:
            outfile.write(str(self))


if __name__ == '__main__':
    PE = PythonExpressionCodeGenerator

    hello_function = PythonFunctionCodeGenerator(
        'say_hello_world',
        (),
        (PE('print(\"hello world!\")'),),
        ()
    )
    # print(hello_function)
    """
    def hello():
        print(\'hello world!')
    """

    hello_name_function = PythonFunctionCodeGenerator(
        'say_hello',
        ('self', 'name'),
        (PE('print(f\'hello {name}!\')'),),
        ()
    )
    # print(hello_name_function)
    """
    def hello_to(name):
        print(f'hello {name}!')
    """

    init_method = PythonFunctionCodeGenerator(
        '__init__',
        ('self',),
        (PE('self.random_int = random.randint(1, 100)'),),
        ()
    )

    some_metaclass = PythonClassCodeGenerator(
        'Meta',
        ()
    )
    some_metaclass.add_method(copy.deepcopy(init_method))
    # print(some_metaclass)
    """
    class Meta:
    def __init__(self):
        self.random_int = random.randint(1, 100)
    """

    person_class = PythonClassCodeGenerator(
        'Person',
        ()
    )
    person_class.add_class_attribute(copy.deepcopy(PythonAssignmentCodeGenerator('first_name', '\'Will\'')))
    person_class.add_class_attribute(copy.deepcopy(PythonAssignmentCodeGenerator('last_name', '\'Smith\'')))
    person_class.add_nested_class(copy.deepcopy(some_metaclass))
    person_class.add_method(copy.deepcopy(hello_function))
    person_class.add_method(copy.deepcopy(hello_name_function))
    # print(person_class)
    """
    class Person:
        first_name = 'Will'
        last_name = 'Smith'

        class Meta:
            def __init__(self):
                self.random_int = random.randint(1, 100)

        @staticmethod
        def say_hello_world():
            print("hello world!")

        def say_hello(self, name):
            print(f'hello {name}!')
    """

    tutorial_module = PythonModuleCodeGenerator('tutorial', '.')
    tutorial_module.add_component(copy.deepcopy(hello_function))
    tutorial_module.add_component(copy.deepcopy(hello_name_function))
    tutorial_module.add_component(copy.deepcopy(some_metaclass))
    tutorial_module.add_component(copy.deepcopy(person_class))
    # print(tutorial_module)
    tutorial_module.save()
