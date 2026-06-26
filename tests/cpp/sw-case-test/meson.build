project('sw-case-test', ['cpp'],
        default_options: ['warning_level=1', 'cpp_std=c++20',
                          'b_colorout=auto', 'optimization=2', 'b_pie=true'])

subdir('semiwrap')

swcase_case_test_sources += files(
  'src/swcase/src/case_test.cpp',
  'src/swcase/src/main.cpp',
)

subdir('semiwrap/modules')
