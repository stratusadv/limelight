import { install } from '../src/index.ts';


const overlay = install({
    controls: true,
    css: '#limelight-title { color: white; }',
    speedFactor: 1,
    stepMode: false,
    theme: {
        colorAccent: '#4ea1ff',
        colorSpotlight: '#ffd56b',
        fontFamily: 'system-ui',
    },
});

overlay?.title({ kicker: 'Sales', subtitle: 'Draft to approved.', title: 'Order Approval' });
overlay?.titleHide();
overlay?.titleRemove();
