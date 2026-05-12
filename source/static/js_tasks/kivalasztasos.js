// Kiválasztásos feladat dinamikus megjelenítése és kezelése
// Minden függvény exportálható, hogy a tasks.html-ből hívható legyen

/**
 * Megjeleníti a kiválasztásos feladatot a megadott JSON alapján.
 * @param {Object} taskJson - A szervertől kapott feladat JSON.
 * @param {HTMLElement} container - Az a DOM elem, ahová a feladatot generáljuk.
 * @param {Function} onSubmit - Callback, ha a felhasználó beküldi a választ (valid input esetén)
 */
// Globális variációszámláló
let variacioSzam = 0;
let lastTaskId = null;
// Minden selecthez tároljuk, hogy volt-e már első választás
let selectFirstChosen = {};

export function renderKivalasztasosTask(taskJson, container, onSubmit, result = null, onNext = null) {
    // Ha új feladat, nullázunk, különben visszaolvassuk a containerből
    if (taskJson.task_id !== lastTaskId) {
        variacioSzam = 0;
        selectFirstChosen = {};
        lastTaskId = taskJson.task_id;
    } else {
        // Próbálkozásnál visszaolvassuk a containerből
        if (container.dataset.variacioSzam) {
            variacioSzam = 0;
        }
    }
    // Minden select előző értékét tároljuk
    const prevValues = {};
    // Csak akkor töröljük a DOM-ot, ha új feladatot generálunk (nincs result)
    if (!result) container.innerHTML = '';
    const { feladat, allapot, task_id } = taskJson;
    const difficulty = taskJson.settings.difficulty;
    if (!result) {
        // Feladat szöveg
        const feladatTipus = feladat.feladat;
        const fonetika_tipus = feladat.hasznalt_fonetika_index == 8 ? 'fonetika' : 'leírás'
        const feladatSzoveg = document.createElement('div');
        feladatSzoveg.className = 'task-instruction';
        feladatSzoveg.innerHTML = `<b>Feladat:</b> Add meg az alábbi ${feladatTipus === 'idegen_szo' ? 'idegen szó' : feladatTipus === 'jelentes' ? 'jelentés' : fonetika_tipus} <b>"${feladat[feladatTipus][0]}"</b> adatait, válaszd ki a listából!`;
        container.appendChild(feladatSzoveg);

        // Input mezők generálása
        const form = document.createElement('form');
        form.className = 'task-input-form';
        form.autocomplete = 'off';
        const inputBlocks = [];
        let inputIdx = 0;
        for (let m = 0; m < feladat.megadandó.length; m++) {
            const field = feladat.megadandó[m];
            const values = feladat[field];
            const lehetosegKey = field + '_lehetőség';
            const lehetosegek = feladat[lehetosegKey];
            for (let v = 0; v < values.length; v++) {
                const inputBlock = document.createElement('div');
                inputBlock.className = 'input-block';
                const label = document.createElement('label');
                label.textContent = `${field === 'idegen_szo' ? 'Idegen szó' : field === 'jelentes' ? 'Jelentés' : 'Fonetika'} ${values.length > 1 ? (v+1) : ''}`;
                label.setAttribute('for', `select_${task_id}_${inputIdx}`);
                inputBlock.appendChild(label);

                // Select mező
                const select = document.createElement('select');
                select.name = `${field}_${v}`;
                select.id = `select_${task_id}_${inputIdx}`;
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Válassz...';
                select.appendChild(defaultOption);
                let optionsList = Array.isArray(lehetosegek[0]) ? lehetosegek[v] : lehetosegek;
                optionsList.forEach((opt, idx) => {
                    const option = document.createElement('option');
                    option.value = idx;
                    option.textContent = opt;
                    select.appendChild(option);
                });
                inputBlock.appendChild(select);

                // Nehézségi checkbox (csak nehéz feladatnál)
                let checkbox = null;
                if (difficulty === 'nehez') {
                    checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `${field}_${v}_nincs_valasz`;
                    checkbox.style.marginLeft = '10px';
                    const checkboxLabel = document.createElement('label');
                    checkboxLabel.textContent = 'Nincs benne a válasz';
                    checkboxLabel.setAttribute('for', checkbox.id);
                    inputBlock.appendChild(checkbox);
                    inputBlock.appendChild(checkboxLabel);
                    checkbox.addEventListener('change', function() {
                        select.disabled = this.checked;
                    });
                }
                // --- Variáció számláló logika ---
                // Minden selecthez külön kulcs
                const selectKey = `${task_id}_${inputIdx}`;
                selectFirstChosen[selectKey] = false;
                let lastValue = '';
                select.addEventListener('change', function(e) {
                    const currentValue = select.value;
                    if (!selectFirstChosen[selectKey]) {
                        // Első választás (üresről nem üresre)
                        if (lastValue === '' && currentValue !== '') {
                            selectFirstChosen[selectKey] = true;
                            // Nem növeljük a számlálót
                        }
                    } else {
                        // Már volt első választás
                        if (currentValue !== lastValue) {
                            // Ha üresre vált, akkor a következő nem üres lesz újra első választás
                            if (currentValue === '') {
                                selectFirstChosen[selectKey] = false;
                            }
                            // Minden váltás növeli, kivéve az elsőt
                            variacioSzam++;
                        }
                    }
                    lastValue = currentValue;
                });
                inputBlocks.push({select, checkbox, hasCheckbox: !!checkbox, field, v, inputBlock, optionsList});
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
            for (const block of inputBlocks) {
                if (block.hasCheckbox && block.checkbox.checked) {
                    continue;
                }
                if (!block.select.value) {
                    valid = false;
                    block.select.classList.add('input-error');
                } else {
                    block.select.classList.remove('input-error');
                }
            }
            if (!valid) {
                if (difficulty === 'nehez') {
                    errorDiv.textContent = 'Minden mezőhöz válassz ki egy lehetőséget, vagy pipáld be, hogy nincs benne a válasz!';
                } else {
                    errorDiv.textContent = 'Minden mezőhöz válassz ki egy lehetőséget!';
                }
                errorDiv.style.display = 'block';
            } else {
                errorDiv.style.display = 'none';
            }
            return valid;
        }
        // Gombok eseménykezelői
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (!validateInputs()) return;
            const answers = {};
            let idx = 0;
            for (let m = 0; m < feladat.megadandó.length; m++) {
                const field = feladat.megadandó[m];
                const values = feladat[field];
                answers[field] = [];
                for (let v = 0; v < values.length; v++) {
                    const block = inputBlocks[idx];
                    if (block.hasCheckbox && block.checkbox.checked) {
                        answers[field].push(-1);
                    } else {
                        answers[field].push(parseInt(block.select.value, 10));
                    }
                    idx++;
                }
                answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
            }
            // Tároljuk a variacioSzam-t a containerben
            container.dataset.variacioSzam = variacioSzam;
            if (typeof onSubmit === 'function') {
                const submitData = { task_id, answers, probalkozas: false };
                submitData.variacioSzam = variacioSzam;
                onSubmit(submitData);
            }
        });
        tryBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (!validateInputs()) return;
            const answers = {};
            let idx = 0;
            for (let m = 0; m < feladat.megadandó.length; m++) {
                const field = feladat.megadandó[m];
                const values = feladat[field];
                answers[field] = [];
                for (let v = 0; v < values.length; v++) {
                    const block = inputBlocks[idx];
                    if (block.hasCheckbox && block.checkbox.checked) {
                        answers[field].push(-1);
                    } else {
                        answers[field].push(parseInt(block.select.value, 10));
                    }
                    idx++;
                }
                answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
            }
            // Tároljuk a variacioSzam-t a containerben
            container.dataset.variacioSzam = variacioSzam;
            if (typeof onSubmit === 'function') {
                const submitData = { task_id, answers, probalkozas: true };
                submitData.variacioSzam = variacioSzam;
                onSubmit(submitData);
            }
        });
    }
    // --- DOM módosítás a result alapján ---
    if (result && Array.isArray(result.pozicio_helyesseg)) {
        const form = container.querySelector('form');
        const btnGroup = form.querySelector('.btn-group');
        btnGroup.innerHTML = '';
        // Próbálkozások számának frissítése
        const probalkozasDiv = form.querySelector('.task-attempts');
        if (probalkozasDiv && typeof result.probalkozasok_szama !== 'undefined') {
            probalkozasDiv.textContent = `Próbálkozás: ${result.probalkozasok_szama} / ${taskJson.allapot.max_probalkozas}`;
        }
        // Előre ellenőrizzük, hogy van-e hibás jelentés mező
        let vanHibasJelentes = false;
        if (result && Array.isArray(result.pozicio_helyesseg)) {
            let inputIdxTmp = 0;
            for (let m = 0; m < feladat.megadandó.length; m++) {
                const field = feladat.megadandó[m];
                const values = feladat[field];
                if (field.startsWith('jelentes')) {
                    for (let v = 0; v < values.length; v++) {
                        if (!result.pozicio_helyesseg[inputIdxTmp]) {
                            vanHibasJelentes = true;
                        }
                        inputIdxTmp++;
                    }
                } else {
                    inputIdxTmp += values.length;
                }
            }
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
            submitBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const answers = {};
                let idx = 0;
                for (let m = 0; m < feladat.megadandó.length; m++) {
                    const field = feladat.megadandó[m];
                    const values = feladat[field];
                    answers[field] = [];
                    for (let v = 0; v < values.length; v++) {
                        const select = form.querySelector(`#select_${task_id}_${idx}`);
                        const block = select.parentElement;
                        const checkbox = block.querySelector('input[type="checkbox"]');
                        if (checkbox && checkbox.checked) {
                            answers[field].push(-1);
                        } else {
                            answers[field].push(select ? parseInt(select.value, 10) : '');
                        }
                        idx++;
                    }
                    answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
                }
                // Tároljuk a variacioSzam-t a containerben
                container.dataset.variacioSzam = variacioSzam;
                if (typeof onSubmit === 'function') {
                    const submitData = { task_id, answers, probalkozas: false };
                    submitData.variacioSzam = variacioSzam;
                    onSubmit(submitData, answers);
                }
            });
            tryBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const answers = {};
                let idx = 0;
                for (let m = 0; m < feladat.megadandó.length; m++) {
                    const field = feladat.megadandó[m];
                    const values = feladat[field];
                    answers[field] = [];
                    for (let v = 0; v < values.length; v++) {
                        const select = form.querySelector(`#select_${task_id}_${idx}`);
                        const block = select.parentElement;
                        const checkbox = block.querySelector('input[type="checkbox"]');
                        if (checkbox && checkbox.checked) {
                            answers[field].push(-1);
                        } else {
                            answers[field].push(select ? parseInt(select.value, 10) : '');
                        }
                        idx++;
                    }
                    answers[field] = answers[field].length === 1 ? [answers[field][0]] : answers[field];
                }
                // Tároljuk a variacioSzam-t a containerben
                container.dataset.variacioSzam = variacioSzam;
                if (typeof onSubmit === 'function') {
                    const submitData = { task_id, answers, probalkozas: true };
                    submitData.variacioSzam = variacioSzam;
                    onSubmit(submitData, answers);
                }
            });
        }
        // Minden selectet módosítunk a helyesség szerint
        let inputIdx = 0;
        for (let m = 0; m < feladat.megadandó.length; m++) {
            const field = feladat.megadandó[m];
            const values = feladat[field];
            const lehetosegKey = field + '_lehetőség';
            const lehetosegek = feladat[lehetosegKey];
            for (let v = 0; v < values.length; v++) {
                const selectId = `select_${task_id}_${inputIdx}`;
                const select = form.querySelector(`#${selectId}`);
                const block = select.parentElement;
                // Töröljük az előző színezést
                select.classList.remove('input-correct', 'input-incorrect', 'input-error-text');
                // Töröljük az előző helyes megoldás kiírást
                const prevHelyes = block.querySelector('.helyes-megoldas');
                if (prevHelyes) prevHelyes.remove();
                const helyes = result.pozicio_helyesseg[inputIdx];
                if (helyes) {
                    select.classList.add('input-correct');
                    select.disabled = true;
                } else {
                    if (result.status === 'beküldve') {
                        select.classList.add('input-incorrect');
                         select.disabled = true;
                        // Helyes megoldás kiírása
                        if (field.startsWith('jelentes') && result.helyes_lett_volna && Array.isArray(result.helyes_lett_volna.jelentes_ek) && vanHibasJelentes) {
                            // Minden jelentés mező alatt az összes helyes jelentés
                            const helyesDiv = document.createElement('div');
                            helyesDiv.className = 'helyes-megoldas';
                            helyesDiv.innerHTML = `<span style=\"color:#388e3c;font-size:13px;\">Helyes jelentések: <b>${result.helyes_lett_volna.jelentes_ek.join(', ')}</b></span>`;
                            block.appendChild(helyesDiv);
                        } else if (result.helyes_lett_volna && result.helyes_lett_volna[field]) {
                            let helyesValasz = result.helyes_lett_volna[field];
                            if (typeof helyesValasz !== 'undefined') {
                                const helyesDiv = document.createElement('div');
                                helyesDiv.className = 'helyes-megoldas';
                                let helyesSzoveg = '';
                                let opciok = Array.isArray(lehetosegek[0]) ? lehetosegek[v] : lehetosegek;
                                if (helyesValasz === -1) {
                                    helyesSzoveg = 'Nincs helyes válasz';
                                } else if (typeof helyesValasz === 'number' && opciok[helyesValasz]) {
                                    helyesSzoveg = opciok[helyesValasz];
                                } else {
                                    helyesSzoveg = helyesValasz;
                                }
                                helyesDiv.innerHTML = `<span style=\"color:#388e3c;font-size:13px;\">Helyes megoldás: <b>${helyesSzoveg}</b></span>`;
                                block.appendChild(helyesDiv);
                            }
                        }
                    } else {
                        // Próbálkozásnál hibás mező: csak piros betűszín, mindig szerkeszthető marad
                        select.classList.add('input-error-text');
                        //select.disabled = false;
                    }
                }
                inputIdx++;
            }
        }
    }
} 