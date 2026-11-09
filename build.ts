import { build } from 'esbuild';


interface Script {
    readonly call: string;
    readonly name: string;
    readonly parameters: string;
}

interface Bundle extends Pick<Script, 'call' | 'parameters'> {
    readonly entryPoint: string;
    readonly outfile: string;
}


const BUNDLE_NAME = 'limelight';
const SCRIPTS_ENTRY = 'src/scripts';
const SCRIPTS_TARGET = 'limelight/scripts';

const BUNDLES: readonly Bundle[] = Object.freeze([
    {
        call: 'install(config)',
        entryPoint: 'src/index.ts',
        outfile: 'limelight/overlay/assets/overlay.js',
        parameters: '(config)',
    },
    scriptBundle({
        call: 'isColorSchemeDark()',
        name: 'color_scheme_dark',
        parameters: '()',
    }),
    scriptBundle({
        call: 'formInvalid(form)',
        name: 'form_invalid',
        parameters: 'form',
    }),
    scriptBundle({
        call: 'inputType(element)',
        name: 'input_type',
        parameters: 'element',
    }),
    scriptBundle({
        call: 'locatorLabel(element)',
        name: 'locator_label',
        parameters: 'element',
    }),
    scriptBundle({
        call: 'isPointHit(element, point)',
        name: 'point_hit',
        parameters: '(element, point)',
    }),
    scriptBundle({
        call: 'scrollIntoView(element)',
        name: 'scroll_into_view',
        parameters: 'element',
    }),
    scriptBundle({
        call: 'selectOptionLabels(element)',
        name: 'select_option_labels',
        parameters: 'element',
    }),
]);


await Promise.all(BUNDLES.map(async (bundle) => bundleWrite(bundle)));


async function bundleWrite(bundle: Bundle): Promise<void> {
    await build({
        banner: { js: `${bundle.parameters} => {` },
        bundle: true,
        entryPoints: [bundle.entryPoint],
        footer: { js: `return ${BUNDLE_NAME}.${bundle.call};\n}` },
        format: 'iife',
        globalName: BUNDLE_NAME,
        logLevel: 'warning',
        minify: true,
        outfile: bundle.outfile,
        target: 'es2024',
    });
}

function scriptBundle(script: Script): Bundle {
    const { call, name, parameters } = script;
    const entryPoint = `${SCRIPTS_ENTRY}/${name}.ts`;
    const outfile = `${SCRIPTS_TARGET}/${name}.js`;

    return { call, entryPoint, outfile, parameters };
}
