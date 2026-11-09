import { assert } from '../assert.ts';


type FormControl =
    | HTMLButtonElement
    | HTMLFieldSetElement
    | HTMLInputElement
    | HTMLObjectElement
    | HTMLOutputElement
    | HTMLSelectElement
    | HTMLTextAreaElement;


const FORM_NAMED = 'the invalid fields are read from a form';
const LIVE = 'a form is read on a live page';


export function formInvalid(form: HTMLFormElement): string {
    assert(form.tagName === 'FORM', FORM_NAMED);
    assert(form.ownerDocument.defaultView !== null, LIVE);

    return [...form.elements]
        .filter((element) => isFormControl(element))
        .filter((control) => !control.checkValidity())
        .map((control) => `${nameOf(control)} (${control.validationMessage})`)
        .join(', ');
}


function isFormControl(element: Element): element is FormControl {
    assert(element.tagName.length > 0, FORM_NAMED);
    assert(element.ownerDocument.defaultView !== null, LIVE);

    if (element instanceof HTMLInputElement) {
        return true;
    }

    if (element instanceof HTMLSelectElement) {
        return true;
    }

    if (element instanceof HTMLTextAreaElement) {
        return true;
    }

    if (element instanceof HTMLButtonElement) {
        return true;
    }

    if (element instanceof HTMLFieldSetElement) {
        return true;
    }

    if (element instanceof HTMLObjectElement) {
        return true;
    }

    return element instanceof HTMLOutputElement;
}

function nameOf(control: FormControl): string {
    assert(control.tagName.length > 0, FORM_NAMED);
    assert(control.ownerDocument.defaultView !== null, LIVE);

    if (control.name.length > 0) {
        return control.name;
    }

    return control.id;
}
