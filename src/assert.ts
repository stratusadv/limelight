export class AssertionError extends Error {
    public constructor(message: string, options?: Readonly<ErrorOptions>) {
        super(message, options);
        this.name = 'AssertionError';
    }
}


export function assert(isSatisfied: boolean, message: string): asserts isSatisfied {
    if (isSatisfied) {
        return;
    }

    throw new AssertionError(message);
}
