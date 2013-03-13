
import unittest

import binding
import errors
import injecting


class BindingKeyWithoutAnnotationTest(unittest.TestCase):

    def test_equal_if_same_arg_name(self):
        binding_key_one = binding.BindingKeyWithoutAnnotation('an-arg-name')
        binding_key_two = binding.BindingKeyWithoutAnnotation('an-arg-name')
        self.assertEqual(binding_key_one, binding_key_two)
        self.assertEqual(hash(binding_key_one), hash(binding_key_two))
        self.assertEqual(str(binding_key_one), str(binding_key_two))

    def test_unequal_if_not_same_arg_name(self):
        binding_key_one = binding.BindingKeyWithoutAnnotation('arg-name-one')
        binding_key_two = binding.BindingKeyWithoutAnnotation('arg-name-two')
        self.assertNotEqual(binding_key_one, binding_key_two)
        self.assertNotEqual(hash(binding_key_one), hash(binding_key_two))
        self.assertNotEqual(str(binding_key_one), str(binding_key_two))

    def test_str(self):
        binding_key = binding.BindingKeyWithoutAnnotation('an-arg-name')
        self.assertEqual('the arg name an-arg-name', str(binding_key))


class NewBindingMappingTest(unittest.TestCase):

    def test_no_input_bindings_returns_empty_mapping(self):
        binding_mapping = binding.new_binding_mapping([], [])
        self.assertRaises(errors.NothingInjectableForArgNameError,
                          binding_mapping.get_instance,
                          binding.BindingKeyWithoutAnnotation('anything'))

    def test_unknown_binding_raises_error(self):
        class SomeClass(object):
            pass
        binding_key = binding.BindingKeyWithoutAnnotation('some_class')
        binding_mapping = binding.new_binding_mapping(
            [], [binding.Binding(binding_key, SomeClass)])
        unknown_binding_key = binding.BindingKeyWithoutAnnotation(
            'unknown_class')
        self.assertRaises(errors.NothingInjectableForArgNameError,
                          binding_mapping.get_instance, unknown_binding_key)

    def test_single_implicit_class_gets_mapped(self):
        class SomeClass(object):
            pass
        binding_key = binding.BindingKeyWithoutAnnotation('some_class')
        binding_mapping = binding.new_binding_mapping(
            [], [binding.Binding(binding_key, SomeClass)])
        self.assertIsInstance(binding_mapping.get_instance(binding_key), SomeClass)

    def test_multiple_noncolliding_implicit_classes_get_mapped(self):
        class ClassOne(object):
            pass
        class ClassTwo(object):
            pass
        binding_key_one = binding.BindingKeyWithoutAnnotation('class_one')
        binding_key_two = binding.BindingKeyWithoutAnnotation('class_two')
        binding_mapping = binding.new_binding_mapping(
            [], [binding.Binding(binding_key_one, ClassOne),
                 binding.Binding(binding_key_two, ClassTwo)])
        self.assertIsInstance(binding_mapping.get_instance(binding_key_one), ClassOne)
        self.assertIsInstance(binding_mapping.get_instance(binding_key_two), ClassTwo)

    def test_multiple_colliding_classes_raises_error(self):
        class SomeClass(object):
            pass
        class _SomeClass(object):
            pass
        binding_key = binding.BindingKeyWithoutAnnotation('some_class')
        binding_mapping = binding.new_binding_mapping(
            [], [binding.Binding(binding_key, SomeClass),
                 binding.Binding(binding_key, _SomeClass)])
        self.assertRaises(errors.AmbiguousArgNameError,
                          binding_mapping.get_instance, binding_key)


class DefaultGetArgNamesFromClassNameTest(unittest.TestCase):

    def test_single_word_lowercased(self):
        self.assertEqual(['foo'], binding.default_get_arg_names_from_class_name('Foo'))

    def test_leading_underscore_stripped(self):
        self.assertEqual(['foo'], binding.default_get_arg_names_from_class_name('_Foo'))

    def test_multiple_words_lowercased_with_underscores(self):
        self.assertEqual(['foo_bar_baz'], binding.default_get_arg_names_from_class_name('FooBarBaz'))

    def test_malformed_class_name_raises_error(self):
        self.assertEqual([], binding.default_get_arg_names_from_class_name('notAllCamelCase'))


class FakeInjector(object):

    def provide(self, cls):
        return 'a-provided-{0}'.format(cls.__name__)


class GetImplicitBindingsTest(unittest.TestCase):

    def test_returns_no_bindings_for_no_input(self):
        self.assertEqual([], binding.get_implicit_bindings([], FakeInjector()))

    def test_returns_binding_for_input_class(self):
        class SomeClass(object):
            pass
        [implicit_binding] = binding.get_implicit_bindings(
            [SomeClass], FakeInjector())
        self.assertEqual(binding.BindingKeyWithoutAnnotation('some_class'),
                         implicit_binding.binding_key)
        self.assertEqual('a-provided-SomeClass', implicit_binding.provider_fn())

    def test_returns_binding_for_correct_input_class(self):
        class ClassOne(object):
            pass
        class ClassTwo(object):
            pass
        implicit_bindings = binding.get_implicit_bindings(
            [ClassOne, ClassTwo], FakeInjector())
        for implicit_binding in implicit_bindings:
            if (implicit_binding.binding_key ==
                binding.BindingKeyWithoutAnnotation('class_one')):
                self.assertEqual('a-provided-ClassOne',
                                 implicit_binding.provider_fn())
            else:
                self.assertEqual(
                    implicit_binding.binding_key,
                    binding.BindingKeyWithoutAnnotation('class_two'))
                self.assertEqual('a-provided-ClassTwo',
                                 implicit_binding.provider_fn())

    def test_uses_provided_fn_to_map_class_names_to_arg_names(self):
        class SomeClass(object):
            pass
        [implicit_binding] = binding.get_implicit_bindings(
            [SomeClass], FakeInjector(),
            get_arg_names_from_class_name=lambda _: ['foo'])
        self.assertEqual(binding.BindingKeyWithoutAnnotation('foo'),
                         implicit_binding.binding_key)


class BinderTest(unittest.TestCase):

    def setUp(self):
        self.future_injector = injecting._FutureInjector()
        self.collected_bindings = []
        self.binder = binding.Binder(self.future_injector, self.collected_bindings)

    def test_can_bind_to_class(self):
        class SomeClass(object):
            pass
        self.binder.bind('an-arg-name', to_class=SomeClass)
        self.future_injector.set_injector(FakeInjector())
        [only_binding] = self.collected_bindings
        self.assertEqual(binding.BindingKeyWithoutAnnotation('an-arg-name'),
                         only_binding.binding_key)
        self.assertEqual('a-provided-SomeClass', only_binding.provider_fn())

    def test_can_bind_to_instance(self):
        an_instance = object()
        self.binder.bind('an-arg-name', to_instance=an_instance)
        [only_binding] = self.collected_bindings
        self.assertEqual(binding.BindingKeyWithoutAnnotation('an-arg-name'),
                         only_binding.binding_key)
        self.assertIs(an_instance, only_binding.provider_fn())

    def test_can_bind_to_provider(self):
        self.binder.bind('an-arg-name', to_provider=lambda: 'a-provided-thing')
        [only_binding] = self.collected_bindings
        self.assertEqual(binding.BindingKeyWithoutAnnotation('an-arg-name'),
                         only_binding.binding_key)
        self.assertEqual('a-provided-thing', only_binding.provider_fn())

    def test_binding_to_nothing_raises_error(self):
        self.assertRaises(errors.NoBindingTargetError,
                          self.binder.bind, 'unused-arg-name')

    def test_binding_to_multiple_things_raises_error(self):
        self.assertRaises(errors.MultipleBindingTargetsError,
                          self.binder.bind, 'unused-arg-name',
                          to_instance=object(), to_provider=lambda: None)

    def test_binding_to_non_class_raises_error(self):
        self.assertRaises(errors.InvalidBindingTargetError,
                          self.binder.bind, 'unused-arg-name',
                          to_class='not-a-class')

    def test_binding_to_non_provider_raises_error(self):
        self.assertRaises(errors.InvalidBindingTargetError,
                          self.binder.bind, 'unused-arg-name',
                          to_provider='not-a-provider')
