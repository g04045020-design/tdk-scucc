// Beírásos feladat dinamikus megjelenítése és kezelése
// Minden függvény exportálható, hogy a tasks.html-ből hívható legyen

/**
 * Megjeleníti a beírásos feladatot a megadott JSON alapján, valamint a szerver visszajelzését (ha van).
 * @param {Object} taskJson - A szervertől kapott feladat JSON.
 * @param {HTMLElement} container - Az a DOM elem, ahová a feladatot generáljuk.
 * @param {Function} onSubmit - Callback, ha a felhasználó beküldi a választ (valid input esetén)
 * @param {Object} [result] - Opcionális, a /submit_task válasza (helyesség, helyes megoldás, státusz)
 * @param {Function} [onNext] - Opcionális, callback a "Következő feladat" gombra
 */
export function renderBeirasosTask(taskJson, container, onSubmit, result = null, onNext = null) {
    // Csak akkor töröljük a DOM-ot, ha új feladatot generálunk (nincs result)
    if (!result) container.innerHTML = '';
    const { feladat, allapot, task_id } = taskJson;
    // Feladat szöveg
    if (!result) {
    const feladatTipus = feladat.feladat;
    const fonetika_tipus = feladat.hasznalt_fonetika_index == 8 ? 'fonetika' : 'leírás' 
    const feladatSzoveg = document.createElement('div');
    feladatSzoveg.className = 'task-instruction';
    feladatSzoveg.innerHTML = `<b>Feladat:</b> Add meg az alábbi ${feladatTipus === 'idegen_szo' ? 'idegen szó' : feladatTipus === 'jelentes' ? 'jelentés' : fonetika_tipus} <b>"${feladat[feladatTipus][0] }"</b> további adatait!`;
    container.appendChild(feladatSzoveg);

    // Input mezők generálása
    const form = document.createElement('form');
    form.className = 'task-input-form';
    form.autocomplete = 'off';
    let megadottBetuk = feladat.megadott_betűk || [];
    let betuIndex = 0;
    let betuSegitseg = [];
    if (feladat.megadott_betűk && feladat.megadott_betűk.length > 0) {
        let totalInputs = 0;
        for (let m = 0; m < feladat.megadandó.length; m++) {
            totalInputs += feladat[feladat.megadandó[m]].length;
        }
        if (totalInputs === 1) {
            betuSegitseg = [feladat.megadott_betűk];
        } else {
            betuSegitseg = Array(totalInputs).fill(null).map((_, i) => feladat.megadott_betűk[i] ? [feladat.megadott_betűk[i]] : []);
        }
    }
    let inputIdx = 0;
    for (let m = 0; m < feladat.megadandó.length; m++) {
        const field = feladat.megadandó[m];
        const values = feladat[field];
        for (let v = 0; v < values.length; v++) {
            const inputBlock = document.createElement('div');
            inputBlock.className = 'input-block';
            const label = document.createElement('label');
            const nagyBetus_fonetika = String(fonetika_tipus).charAt(0).toUpperCase() + String(fonetika_tipus).slice(1)
            label.textContent = `${field === 'idegen_szo' ? 'Idegen szó' : field === 'jelentes' ? 'Jelentés' : nagyBetus_fonetika} ${values.length > 1 ? (v+1) : ''}`;
                label.setAttribute('for', `input_${task_id}_${inputIdx}`);
            inputBlock.appendChild(label);
                // Egyedi id minden inputhoz: csak globális sorszám
                const inputId = `input_${task_id}_${inputIdx}`;
            const input = document.createElement('input');
            input.type = 'text';
            input.name = `${field}_${v}`;
                input.id = inputId;
            input.autocomplete = 'off';
            input.maxLength = 128;
            inputBlock.appendChild(input);
            // Megadott betűk kiírása, ha van
            if (betuSegitseg[inputIdx] && betuSegitseg[inputIdx].length > 0) {
                betuSegitseg[inputIdx].forEach(betu => {
                    const info = document.createElement('span');
                    info.className = 'fixed-char-info';
                    info.textContent = `A(z) ${betu[0]+1}. betű: '${betu[1]}'`;
                    inputBlock.appendChild(info);
                });
            }
            form.appendChild(inputBlock);
            inputIdx++;
        }
    }
    // Próbálkozások száma
    const probalkozasDiv = document.createElement('div');
    probalkozasDiv.className = 'task-attempts';
    probalkozasDiv.textContent = `Próbálkozás: ${allapot.probalkozasok_szama} / ${allapot.max_probalkozas}`;
    form.appendChild(probalkozasDiv);
    // Hibaüzenet
    const errorDiv = document.createElement('div');
    errorDiv.className = 'task-error';
    errorDiv.style.display = 'none';
    form.appendChild(errorDiv);
        // Gombok
    const btnGroup = document.createElement('div');
    btnGroup.className = 'btn-group';
    const submitBtn = document.createElement('button');
    submitBtn.type = 'button';
    submitBtn.textContent = 'Beküldés';
    btnGroup.appendChild(submitBtn);
    const tryBtn = document.createElement('button');
    tryBtn.type = 'button';
    tryBtn.textContent = 'Próbálkozás';
    btnGroup.appendChild(tryBtn);
    form.appendChild(btnGroup);
        container.appendChild(form);
    // Validációs logika
    function validateInputs() {
        let valid = true;
            const allInputs = form.querySelectorAll('input[type="text"]');
            const values = [];
            for (const input of allInputs) {
                if (!input.value.trim()) {
                valid = false;
                    input.classList.add('input-error');
            } else {
                    input.classList.remove('input-error');
                    values.push(input.value.trim().toLowerCase());
                }
            }
            // Egyediség ellenőrzése
            const valueCounts = {};
            for (const val of values) {
                valueCounts[val] = (valueCounts[val] || 0) + 1;
            }
            let hasDuplicate = false;
            for (const input of allInputs) {
                const val = input.value.trim().toLowerCase();
                if (val && valueCounts[val] > 1) {
                    input.classList.add('input-error');
                    hasDuplicate = true;
            }
        }
        if (!valid) {
            errorDiv.textContent = 'Minden mezőt ki kell tölteni!';
            errorDiv.style.display = 'block';
            } else if (hasDuplicate) {
                errorDiv.textContent = 'Minden mező tartalma legyen különböző!';
                errorDiv.style.display = 'block';
                valid = false;
        } else {
            errorDiv.style.display = 'none';
        }
        return valid;
    }
        // Minden inputhoz hibajelzés eltávolító event
        const allInputs = form.querySelectorAll('input[type="text"]');
        for (const input of allInputs) {
            input.addEventListener('input', function() {
                if (input.classList.contains('input-error')) {
                    input.classList.remove('input-error');
                }
            });
        }
    // Gombok eseménykezelői
    submitBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (!validateInputs()) return;
        const answers = {};
        let inputIdx = 0;
        for (let m = 0; m < feladat.megadandó.length; m++) {
            const field = feladat.megadandó[m];
            const values = feladat[field];
            answers[field] = [];
            for (let v = 0; v < values.length; v++) {
                    const inputId = `input_${task_id}_${inputIdx}`;
                    const input = form.querySelector(`#${inputId}`);
                    answers[field].push(input ? input.value.trim() : '');
                inputIdx++;
            }
            answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
        }
        if (typeof onSubmit === 'function') {
                onSubmit({ task_id, answers, probalkozas: false }, answers);
        }
    });
    tryBtn.addEventListener('click', function(e) {
        e.preventDefault();
            // --- Színek és tiltás visszaállítása próbálkozás előtt ---
            const allInputs = form.querySelectorAll('input[type="text"]');
            for (const input of allInputs) {
                input.classList.remove('input-correct', 'input-incorrect');
                input.disabled = false;
            }
        if (!validateInputs()) return;
        const answers = {};
        let inputIdx = 0;
        for (let m = 0; m < feladat.megadandó.length; m++) {
            const field = feladat.megadandó[m];
            const values = feladat[field];
            answers[field] = [];
            for (let v = 0; v < values.length; v++) {
                    const inputId = `input_${task_id}_${inputIdx}`;
                    const input = form.querySelector(`#${inputId}`);
                    answers[field].push(input ? input.value.trim() : '');
                inputIdx++;
            }
            answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
        }
        if (typeof onSubmit === 'function') {
                onSubmit({ task_id, answers, probalkozas: true }, answers);
        }
    });
    }
    // --- DOM módosítás a result alapján ---
    if (result && Array.isArray(result.pozicio_helyesseg)) {
        // Gombok cseréje
        const form = container.querySelector('form');
        const btnGroup = form.querySelector('.btn-group');
        btnGroup.innerHTML = '';
        // --- Próbálkozások számának frissítése ---
        const probalkozasDiv = form.querySelector('.task-attempts');
        if (probalkozasDiv && typeof result.probalkozasok_szama !== 'undefined') {
            probalkozasDiv.textContent = `Próbálkozás: ${result.probalkozasok_szama} / ${taskJson.allapot.max_probalkozas}`;
        }
        if (result.status === 'beküldve') {
            const nextBtn = document.createElement('button');
            nextBtn.type = 'button';
            nextBtn.textContent = 'Következő feladat';
            nextBtn.className = 'next-task-btn';
            nextBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (typeof onNext === 'function') onNext();
            });
            btnGroup.appendChild(nextBtn);
        } else {
            const submitBtn = document.createElement('button');
            submitBtn.type = 'button';
            submitBtn.textContent = 'Beküldés';
            btnGroup.appendChild(submitBtn);
            const tryBtn = document.createElement('button');
            tryBtn.type = 'button';
            tryBtn.textContent = 'Próbálkozás';
            btnGroup.appendChild(tryBtn);
            // Újra kell kötni az eseménykezelőket (lásd fentebb)
            submitBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const answers = {};
                let inputIdx = 0;
                for (let m = 0; m < feladat.megadandó.length; m++) {
                    const field = feladat.megadandó[m];
                    const values = feladat[field];
                    answers[field] = [];
                    for (let v = 0; v < values.length; v++) {
                        const inputId = `input_${task_id}_${inputIdx}`;
                        const input = form.querySelector(`#${inputId}`);
                        answers[field].push(input ? input.value.trim() : '');
                        inputIdx++;
                    }
                    answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
                }
                if (typeof onSubmit === 'function') {
                    onSubmit({ task_id, answers, probalkozas: false }, answers);
                }
            });
            tryBtn.addEventListener('click', function(e) {
                e.preventDefault();
                // --- Színek és tiltás visszaállítása próbálkozás előtt ---
                const allInputs = form.querySelectorAll('input[type="text"]');
                for (const input of allInputs) {
                    input.classList.remove('input-correct', 'input-incorrect');
                    input.disabled = false;
                }
                const answers = {};
                let inputIdx = 0;
                for (let m = 0; m < feladat.megadandó.length; m++) {
                    const field = feladat.megadandó[m];
                    const values = feladat[field];
                    answers[field] = [];
                    for (let v = 0; v < values.length; v++) {
                        const inputId = `input_${task_id}_${inputIdx}`;
                        const input = form.querySelector(`#${inputId}`);
                        answers[field].push(input ? input.value.trim() : '');
                        inputIdx++;
                    }
                    answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
                }
                if (typeof onSubmit === 'function') {
                    onSubmit({ task_id, answers, probalkozas: true }, answers);
                }
            });
        }
        // Jelentés mezők hibakezelése
        let jelentesIndexes = [];
        let jelentesHibas = false;
        for (let m = 0, idx = 0; m < feladat.megadandó.length; m++) {
            const field = feladat.megadandó[m];
            if (field.startsWith('jelentes')) {
                jelentesIndexes.push(idx);
            }
            idx += feladat[field].length;
        }
        jelentesHibas = jelentesIndexes.some(i => !result.pozicio_helyesseg[i]);
        // Minden inputot módosítunk a helyesség szerint
        let inputIdx = 0;
        for (let m = 0; m < feladat.megadandó.length; m++) {
            const field = feladat.megadandó[m];
            const values = feladat[field];
            for (let v = 0; v < values.length; v++) {
                const inputId = `input_${task_id}_${inputIdx}`;
                const input = form.querySelector(`#${inputId}`);
                // Töröljük az előző színezést
                input.classList.remove('input-correct', 'input-incorrect', 'input-error-text');
                // Töröljük az előző helyes megoldás kiírást
                const block = input.parentElement;
                const prevHelyes = block.querySelector('.helyes-megoldas');
                if (prevHelyes) prevHelyes.remove();
                const helyes = result.pozicio_helyesseg[inputIdx];
                if (helyes) {
                    input.classList.add('input-correct');
                    input.disabled = true;
                } else {
                    if (result.status === 'beküldve') {
                        input.classList.add('input-incorrect');
                        input.disabled = true;
                        // Helyes megoldás kiírása, ha van
                        if (field.startsWith('jelentes') && result.helyes_lett_volna && Array.isArray(result.helyes_lett_volna.jelentes_ek)) {
                            const helyesDiv = document.createElement('div');
                            helyesDiv.className = 'helyes-megoldas';
                            helyesDiv.innerHTML = `<span style=\"color:#388e3c;font-size:13px;\">Helyes jelentések: <b>${result.helyes_lett_volna.jelentes_ek.join(', ')}</b></span>`;
                            block.appendChild(helyesDiv);
                        } else if (result.helyes_lett_volna) {
                            let helyesValasz = '';
                            if (field === 'idegen_szo') {
                                helyesValasz = result.helyes_lett_volna.idegen_szo;
                            } else if (field === 'fonetika') {
                                helyesValasz = result.helyes_lett_volna.fonetika;
                            }
                            if (helyesValasz) {
                                const helyesDiv = document.createElement('div');
                                helyesDiv.className = 'helyes-megoldas';
                                helyesDiv.innerHTML = `<span style=\"color:#388e3c;font-size:13px;\">Helyes megoldás: <b>${helyesValasz}</b></span>`;
                                block.appendChild(helyesDiv);
                            }
                        }
                    } else {
                        // Próbálkozásnál hibás mező: csak piros betűszín
                        input.classList.add('input-error-text');
                        input.disabled = false;
                    }
                }
                inputIdx++;
            }
        }
        // Minden inputhoz hibajelzés eltávolító event (result feldolgozás után is)
        // (TÖRÖLVE, mert már nincs rá szükség)
    }
}

/**
 * Létrehoz egy input mezőt, amelyben bizonyos karakterek fixen, nem szerkeszthetően jelennek meg.
 * @param {HTMLInputElement} input - Az eredeti input mező.
 * @param {Array} fixedChars - A fix karakterek tömbje (pl. ['a', 'b'])
 * @param {Array} fixedPositions - A fix karakterek pozíciói tömbje (pl. [0, 1])
 * @returns {HTMLElement} - Egy div, amely tartalmazza a fix karaktereket és az inputot.
 */
function createInputWithFixedChars(input, fixedChars, fixedPositions) {
    // Egyszerűsített: csak a mező elején fix karakterek (további fejlesztés: tetszőleges pozíció)
    const wrapper = document.createElement('div');
    wrapper.className = 'fixed-char-input-wrapper';
    // Mostantól a fix betűk pozíciója is számít
    for (let i = 0; i < fixedChars.length; i++) {
        const span = document.createElement('span');
        span.className = 'fixed-char';
        span.textContent = fixedChars[i];
        // A pozíciót is eltárolhatjuk, ha kell
        wrapper.appendChild(span);
    }
    wrapper.appendChild(input);
    input.style.marginLeft = (fixedChars.length * 1.2) + 'em';
    input.readOnly = false;
    return wrapper;
} 