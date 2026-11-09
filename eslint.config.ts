import { defineConfig } from 'eslint/config';
import eslintJs from '@eslint/js';
import regexp from 'eslint-plugin-regexp';
import sonarjs from 'eslint-plugin-sonarjs';
import stylistic from '@stylistic/eslint-plugin';
import tseslint from 'typescript-eslint';
import unicorn from 'eslint-plugin-unicorn';


const BLANK_LINE_COUNT_MAX = 2;
const COLUMN_COUNT_MAX = 100;
const FILE_LINE_COUNT_MAX = 1000;
const FUNCTION_LINE_COUNT_MAX = 70;
const INDENT_WIDTH = 4;

const MEMBER_ORDER = Object.freeze([
    'signature',
    '#private-static-field',
    '#private-instance-field',
    'public-static-field',
    'public-instance-field',
    'constructor',
    '#private-static-method',
    '#private-instance-method',
    'public-static-method',
    'public-instance-method',
]);

const NAMING = Object.freeze([
    {
        format: ['camelCase'],
        selector: 'default',
    },
    {
        format: ['camelCase', 'UPPER_CASE'],
        modifiers: ['const', 'global'],
        selector: 'variable',
    },
    {
        format: ['camelCase', 'PascalCase'],
        selector: 'import',
    },
    {
        format: ['PascalCase'],
        selector: 'typeLike',
    },
    {
        format: ['camelCase', 'PascalCase', 'UPPER_CASE'],
        selector: 'objectLiteralProperty',
    },
    {
        format: null,
        modifiers: ['requiresQuotes'],
        selector: 'objectLiteralProperty',
    },
]);

const RESTRICTED_SYNTAX = Object.freeze([
    {
        message: 'A do loop carries no bound. Use a for loop against an asserted maximum.',
        selector: 'DoWhileStatement',
    },
    {
        message: 'A for-in loop walks the prototype chain. Index into Object.keys instead.',
        selector: 'ForInStatement',
    },
    {
        message: 'A for-of loop hides its bound. Use an index loop against an asserted maximum.',
        selector: 'ForOfStatement',
    },
    {
        message: 'A for loop declares its index in the initializer.',
        selector: 'ForStatement:not([init])',
    },
    {
        message: 'A for loop carries its bound in the condition.',
        selector: 'ForStatement:not([test])',
    },
    {
        message: 'A for loop advances its index in the update.',
        selector: 'ForStatement:not([update])',
    },
    {
        message: 'An else if chain ends in else, so the negative space is handled.',
        selector: 'IfStatement > IfStatement.alternate:not([alternate])',
    },
    {
        message: 'A compound condition splits into nested if statements.',
        selector: 'IfStatement > LogicalExpression.test',
    },
    {
        message: 'A negated compound condition splits into nested if statements.',
        selector: 'IfStatement > UnaryExpression.test > LogicalExpression',
    },
    {
        message: 'A labeled statement is a goto.',
        selector: 'LabeledStatement',
    },
    {
        message: 'A while loop carries no bound. Use a for loop against an asserted maximum.',
        selector: 'WhileStatement',
    },
]);

const DOM_TYPES = Object.freeze([
    'Animation',
    'Element',
    'HTMLButtonElement',
    'HTMLElement',
    'HTMLFieldSetElement',
    'HTMLFormElement',
    'HTMLInputElement',
    'HTMLObjectElement',
    'HTMLOutputElement',
    'HTMLSelectElement',
    'HTMLTextAreaElement',
    'KeyboardEvent',
    'Node',
]);

const SONARJS_RULES = sonarjsRules();
const WIRE_NAMES_SHORT = Object.freeze(['x', 'y']);


interface SonarjsRule {
    readonly meta?: {
        readonly deprecated?: unknown;
    };
}


export default defineConfig(
    {
        ignores: ['.venv/', 'build/', 'dist/', 'limelight/', 'node_modules/', 'site/', 'tests/'],
    },
    {
        linterOptions: {
            noInlineConfig: true,
            reportUnusedDisableDirectives: 'error',
            reportUnusedInlineConfigs: 'error',
        },
    },
    eslintJs.configs.all,
    tseslint.configs.all,
    stylistic.configs.all,
    unicorn.configs.all,
    regexp.configs.all,
    {
        plugins: {
            sonarjs,
        },
        rules: SONARJS_RULES,
    },
    {
        languageOptions: {
            parserOptions: {
                projectService: true,
                tsconfigRootDir: import.meta.dirname,
            },
        },
        rules: {
            '@stylistic/array-bracket-newline': ['error', 'consistent'],
            '@stylistic/array-element-newline': ['error', 'consistent'],
            '@stylistic/brace-style': ['error', '1tbs', { allowSingleLine: false }],
            '@stylistic/comma-dangle': ['error', 'always-multiline'],
            '@stylistic/dot-location': ['error', 'property'],
            '@stylistic/function-call-argument-newline': ['error', 'consistent'],
            '@stylistic/function-paren-newline': ['error', 'multiline-arguments'],
            '@stylistic/indent': ['error', INDENT_WIDTH, { SwitchCase: 1 }],
            '@stylistic/indent-binary-ops': ['error', INDENT_WIDTH],
            '@stylistic/lines-between-class-members': [
                'error',
                'always',
                { exceptAfterSingleLine: true },
            ],
            '@stylistic/max-len': [
                'error',
                {
                    code: COLUMN_COUNT_MAX,
                    ignoreComments: false,
                    ignoreRegExpLiterals: false,
                    ignoreStrings: false,
                    ignoreTemplateLiterals: false,
                    ignoreUrls: false,
                    tabWidth: INDENT_WIDTH,
                },
            ],
            '@stylistic/no-multiple-empty-lines': [
                'error',
                {
                    max: BLANK_LINE_COUNT_MAX,
                    maxBOF: 0,
                    maxEOF: 0,
                },
            ],
            '@stylistic/object-curly-newline': ['error', { consistent: true, multiline: true }],
            '@stylistic/object-curly-spacing': ['error', 'always'],
            '@stylistic/object-property-newline': ['error', { allowAllPropertiesOnSameLine: true }],
            '@stylistic/operator-linebreak': ['error', 'before', { overrides: { '=': 'after' } }],
            '@stylistic/padded-blocks': ['error', 'never'],
            '@stylistic/padding-line-between-statements': [
                'error',
                {
                    blankLine: 'always',
                    next: ['block-like', 'return', 'throw'],
                    prev: '*',
                },
                {
                    blankLine: 'always',
                    next: '*',
                    prev: 'block-like',
                },
            ],
            '@stylistic/quote-props': ['error', 'consistent-as-needed'],
            '@stylistic/quotes': ['error', 'single', { allowTemplateLiterals: 'never' }],
            '@stylistic/space-before-function-paren': [
                'error',
                {
                    anonymous: 'always',
                    asyncArrow: 'always',
                    named: 'never',
                },
            ],
            '@typescript-eslint/consistent-type-assertions': ['error', { assertionStyle: 'never' }],
            '@typescript-eslint/member-ordering': [
                'error',
                {
                    default: {
                        memberTypes: MEMBER_ORDER,
                        order: 'alphabetically-case-insensitive',
                    },
                },
            ],
            '@typescript-eslint/naming-convention': ['error', ...NAMING],
            '@typescript-eslint/no-floating-promises': [
                'error',
                {
                    allowForKnownSafeCalls: [
                        {
                            from: 'package',
                            name: ['describe', 'it', 'suite', 'test'],
                            package: 'node:test',
                        },
                    ],
                },
            ],
            '@typescript-eslint/no-magic-numbers': [
                'error',
                {
                    detectObjects: false,
                    enforceConst: true,
                    ignore: [-1, 0, 1],
                    ignoreArrayIndexes: true,
                    ignoreEnums: false,
                    ignoreNumericLiteralTypes: true,
                    ignoreReadonlyClassProperties: false,
                    ignoreTypeIndexes: true,
                },
            ],
            '@typescript-eslint/no-use-before-define': [
                'error',
                {
                    classes: true,
                    enums: true,
                    functions: false,
                    ignoreTypeReferences: false,
                    typedefs: true,
                    variables: true,
                },
            ],
            '@typescript-eslint/prefer-for-of': 'off',
            '@typescript-eslint/prefer-readonly-parameter-types': [
                'error',
                {
                    allow: [
                        {
                            from: 'lib',
                            name: DOM_TYPES,
                        },
                    ],
                    checkParameterProperties: true,
                    ignoreInferredTypes: true,
                    treatMethodsAsReadonly: true,
                },
            ],
            '@typescript-eslint/restrict-template-expressions': [
                'error',
                {
                    allowAny: false,
                    allowBoolean: false,
                    allowNever: false,
                    allowNullish: false,
                    allowNumber: false,
                    allowRegExp: false,
                },
            ],
            '@typescript-eslint/strict-boolean-expressions': [
                'error',
                {
                    allowAny: false,
                    allowNullableBoolean: false,
                    allowNullableEnum: false,
                    allowNullableNumber: false,
                    allowNullableObject: false,
                    allowNullableString: false,
                    allowNumber: false,
                    allowString: false,
                },
            ],
            'func-style': ['error', 'declaration'],
            'id-length': ['error', { exceptions: WIRE_NAMES_SHORT }],
            'max-lines': [
                'error',
                {
                    max: FILE_LINE_COUNT_MAX,
                    skipBlankLines: false,
                    skipComments: false,
                },
            ],
            'max-lines-per-function': [
                'error',
                {
                    IIFEs: true,
                    max: FUNCTION_LINE_COUNT_MAX,
                    skipBlankLines: false,
                    skipComments: false,
                },
            ],
            'max-statements': 'off',
            'no-duplicate-imports': [
                'error',
                {
                    allowSeparateTypeImports: true,
                    includeExports: true,
                },
            ],
            'no-restricted-exports': [
                'error',
                {
                    restrictDefaultExports: {
                        defaultFrom: true,
                        direct: true,
                        named: true,
                        namedFrom: true,
                        namespaceFrom: true,
                    },
                },
            ],
            'no-restricted-syntax': ['error', ...RESTRICTED_SYNTAX],
            'no-undefined': 'off',
            'no-void': ['error', { allowAsStatement: true }],
            'one-var': ['error', 'never'],
            'sonarjs/arrow-function-convention': 'off',
            'sonarjs/file-header': 'off',
            'sonarjs/no-collapsible-if': 'off',
            'sonarjs/no-reference-error': 'off',
            'sonarjs/no-undefined-assignment': 'off',
            'sort-imports': ['error', { allowSeparatedGroups: true, ignoreCase: true }],
            'sort-keys': ['error', 'asc', { caseSensitive: false, natural: false }],
            'unicorn/better-regex': 'off',
            'unicorn/consistent-class-member-order': 'off',
            'unicorn/filename-case': ['error', { case: 'snakeCase' }],
            'unicorn/no-for-loop': 'off',
            'unicorn/no-lonely-if': 'off',
            'unicorn/prefer-combined-guards': 'off',
            'unicorn/prefer-continue': 'off',
            'unicorn/prefer-ternary': 'off',
        },
    },
    {
        files: ['src/index.ts'],
        rules: {
            'unicorn/no-barrel-files': 'off',
        },
    },
    {
        files: ['**/*.test.ts'],
        rules: {
            '@typescript-eslint/no-magic-numbers': 'off',
        },
    },
    {
        files: ['eslint.config.ts'],
        rules: {
            'no-restricted-exports': 'off',
            'unicorn/filename-case': 'off',
            'unicorn/no-null': 'off',
        },
    },
);


function isSonarjsRuleCurrent(rule: SonarjsRule | undefined): boolean {
    const deprecated = rule?.meta?.deprecated;

    return deprecated === undefined || deprecated === false;
}

function sonarjsRules(): Readonly<Record<string, 'error'>> {
    const plugin: Readonly<Record<string, SonarjsRule | undefined>> = sonarjs.rules;
    const names = Object.keys(plugin).filter((name) => isSonarjsRuleCurrent(plugin[name]));

    return Object.fromEntries(names.map((name) => [`sonarjs/${name}`, 'error'] as const));
}
