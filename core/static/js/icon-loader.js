const CACHE = {};
const PATH  = `${window.APP_ROOT || ''}/static/system_images/`;   // set APP_ROOT in Jinja if you use one

export function loadIcon(type, variation='on') {
    const key = `${type}_${variation}`;
    if (!CACHE[key]) {
        CACHE[key] = new Promise(res => {
            const img = new Image();
            img.src  = `${PATH}${key}.png`;
            img.onload = () => res(img);
        });
    }
    return CACHE[key];
}
