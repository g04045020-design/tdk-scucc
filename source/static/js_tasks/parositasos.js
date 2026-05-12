// Párosításos feladat dinamikus megjelenítése és kezelése
// Minden függvény exportálható, hogy a tasks.html-ből hívható legyen

/**
 * Megjeleníti a párosításos feladatot a megadott JSON alapján.
 * @param {Object} taskJson - A szervertől kapott feladat JSON.
 * @param {HTMLElement} container - Az a DOM elem, ahová a feladatot generáljuk.
 * @param {Function} onSubmit - Callback, ha a felhasználó beküldi a választ (valid input esetén)
 * @param {Object} result - Opcionális eredmény objektum, ha már van válasz
 * @param {Function} onNext - Opcionális, callback a "Következő feladat" gombra
 * @param {Object} userAnswers - Opcionális, a felhasználó korábbi válaszai
 */
// Globális variációszámláló
let variacioSzam = 0;
let lastTaskId = null;
// Minden selecthez tároljuk, hogy volt-e már első választás
let selectFirstChosen = {};

export function renderParositasosTask(taskJson, container, onSubmit, result = null, onNext = null, userAnswers = null) {
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
    // Csak akkor töröljük a DOM-ot, ha új feladatot generálunk (nincs result)
    if (!result) container.innerHTML = '';
    const { feladat, allapot, task_id } = taskJson;
    const difficulty = taskJson.settings.difficulty;
    const fonetika_tipus = feladat.hasznalt_fonetika_index == 8 ? ' és fonetikával' : ' és leírással'
    const fonetika_tipus_nagy = feladat.hasznalt_fonetika_index == 8 ? 'Fonetika' : 'Leírás'
    const megadando = feladat.megadandó; // 5 elemű lista, minden elem egy tuple
    // Oszlopok: idegen_szo, jelentés, fonetika (ha van legalább egy nem None fonetika)
    const hasFonetika = feladat.fonetika_lehetőség && feladat.fonetika_lehetőség.some(f => f !== null && f !== undefined);
    const columns = [
        { key: 'idegen_szo', label: 'Idegen szó', options: feladat.idegen_szo_lehetőség },
        { key: 'jelentes', label: 'Jelentés', options: feladat.jelentes_lehetőség }
    ];
    if (hasFonetika) {
        columns.push({ key: 'fonetika', label: fonetika_tipus_nagy, options: feladat.fonetika_lehetőség });
    }

        if (!result) {
        // Feladat szöveg
        const feladatSzoveg = document.createElement('div');
        feladatSzoveg.className = 'task-instruction';
        feladatSzoveg.innerHTML = `<b>Feladat:</b> Párosítsd össze a szavakat a megfelelő jelentéssel${hasFonetika ? fonetika_tipus : ''}!`;
        container.appendChild(feladatSzoveg);

        // Mátrix tábla
        const table = document.createElement('table');
        table.className = 'parositasos-table';
        const thead = document.createElement('thead');
        const headRow = document.createElement('tr');
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col.label;
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        // Minden sorhoz (5 szó)
        const selectMatrix = [];
        for (let i = 0; i < megadando.length; i++) {
            const row = document.createElement('tr');
            // Sor szám hozzáadása (0-4)
            row.setAttribute('data-row-index', i);
            const selectRow = [];
            for (let c = 0; c < columns.length; c++) {
                const col = columns[c];
                const td = document.createElement('td');
                // Select mező
                const select = document.createElement('select');
                select.name = `${col.key}_${i}`;
                select.id = `${col.key}_${i}`;
                // Sor szám tárolása a select mezőben is
                select.setAttribute('data-row-index', i);
                // Alapértelmezett opció
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Válassz...';
                select.appendChild(defaultOption);
                // Lehetőségek
                col.options.forEach((opt, idx) => {
                    const option = document.createElement('option');
                    option.value = idx;
                    if (col.key === 'fonetika') {
                        option.textContent = opt === null || opt === undefined ? 'nem tartozik hozzá' : opt;
                    } else {
                        option.textContent = opt;
                    }
                    select.appendChild(option);
                });
                // Nehézségi extra opció (nehéz módban)
                if (difficulty === 'nehez') {
                    const extraOption = document.createElement('option');
                    extraOption.value = '-1';
                    extraOption.textContent = 'nincs itt a helyes válasz';
                    select.appendChild(extraOption);
                }
                // Felhasználó válaszainak visszaállítása, ha vannak
                if (userAnswers && userAnswers[col.key] && userAnswers[col.key][i] !== undefined) {
                    const userValue = userAnswers[col.key][i];
                    // Ha null, akkor üres string, egyébként string-ként állítjuk be
                    select.value = userValue === null ? '' : userValue.toString();
                }
                
                td.appendChild(select);
                row.appendChild(td);
                selectRow.push(select);
                // --- Variáció számláló logika ---
                const selectKey = `${col.key}_${i}`;
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
            }
            tbody.appendChild(row);
            selectMatrix.push(selectRow);
        }
        table.appendChild(tbody);
        container.appendChild(table);

        // Próbálkozások száma
        const probalkozasDiv = document.createElement('div');
        probalkozasDiv.className = 'task-attempts';
        probalkozasDiv.textContent = `Próbálkozás: ${allapot.probalkozasok_szama} / ${allapot.max_probalkozas}`;
        container.appendChild(probalkozasDiv);

        // Hibaüzenet
        const errorDiv = document.createElement('div');
        errorDiv.className = 'task-error';
        errorDiv.style.display = 'none';
        container.appendChild(errorDiv);

        // Beküldés és Próbálkozás gombok
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
        container.appendChild(btnGroup);

        // Validációs logika
        function validateInputs() {
            let valid = true;
            for (let i = 0; i < selectMatrix.length; i++) {
                for (let c = 0; c < selectMatrix[i].length; c++) {
                    if (!selectMatrix[i][c].value && selectMatrix[i][c].value !== '0') {
                        valid = false;
                        selectMatrix[i][c].classList.add('input-error');
                    } else {
                        selectMatrix[i][c].classList.remove('input-error');
                    }
                }
            }
            if (!valid) {
                errorDiv.textContent = 'Minden mezőhöz válassz ki egy lehetőséget!';
                errorDiv.style.display = 'block';
            } else {
                errorDiv.style.display = 'none';
            }
            return valid;
        }

        // Gombok eseménykezelői
        function collectAnswers() {
            // A válaszokat kulcsonként tuple-ként gyűjtjük
            const answers = {};
            for (let c = 0; c < columns.length; c++) {
                const col = columns[c];
                answers[col.key] = [];
                for (let i = 0; i < selectMatrix.length; i++) {
                    const val = selectMatrix[i][c].value;
                    answers[col.key].push(val === '' ? null : parseInt(val, 10));
                }
                answers[col.key] = answers[col.key].length === 1 ? [answers[col.key][0]] : answers[col.key];
            }
            return answers;
        }

        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (!validateInputs()) return;
            const answers = collectAnswers();
            // Tároljuk a variacioSzam-t a containerben
            container.dataset.variacioSzam = variacioSzam;
            if (typeof onSubmit === 'function') {
                onSubmit({ task_id, answers, probalkozas: false, variacioSzam });
            }
        });
        tryBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (!validateInputs()) return;
            const answers = collectAnswers();
            // Tároljuk a variacioSzam-t a containerben
            container.dataset.variacioSzam = variacioSzam;
            if (typeof onSubmit === 'function') {
                onSubmit({ task_id, answers, probalkozas: true, variacioSzam });
            }
        });
    }
    
    // --- DOM módosítás a result alapján ---
    if (result && result.pozicio_helyesseg) {
        const table = container.querySelector('.parositasos-table');
        if (table) {
            const selectMatrix = [];
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach((row, i) => {
                const selectRow = [];
                const selects = row.querySelectorAll('select');
                selects.forEach((select, c) => {
                    selectRow.push(select);
                });
                selectMatrix.push(selectRow);
            });
            
            for (let i = 0; i < selectMatrix.length; i++) {
                for (let c = 0; c < selectMatrix[i].length; c++) {
                    const select = selectMatrix[i][c];
                    const rowIndex = parseInt(select.getAttribute('data-row-index'));
                    const colIndex = c;
                    
                    // Keressük meg a sorhoz tartozó helyességi adatokat
                    const rowCorrectness = result.pozicio_helyesseg.find(item => item[0] === rowIndex);
                    
                    if (rowCorrectness && rowCorrectness[1][colIndex] !== undefined) {
                        const helyes = rowCorrectness[1][colIndex];
                        
                        // Előző CSS osztályok törlése
                        select.classList.remove('input-correct', 'input-incorrect', 'input-error-text');
                        
                        if (result.status === 'beküldve') {
                            // Beküldésnél minden mezőt le kell tiltani
                            select.disabled = true;
                            
                            if (helyes) {
                                select.classList.add('input-correct');
                            } else {
                                select.classList.add('input-incorrect');
                                
                                // Helyes megoldás kiírása, ha van
                                if (result.helyes_lett_volna) {
                                    
                                    const helyesMegoldas = result.helyes_lett_volna.find(item => item[0] === rowIndex);
                                    
                                    if (helyesMegoldas) {
                                        
                                        // Jelentés mezőknél a kulcs neve 'jelentes_ek'
                                        let helyesErtek;
                                        if (columns[c].key === 'jelentes') {
                                            helyesErtek = helyesMegoldas[1].jelentes_ek;
                                        } else {
                                            helyesErtek = helyesMegoldas[1][columns[c].key];
                                        }
                                        
                                        if (helyesErtek !== undefined) {
                                            let helyesText;
                                            if (columns[c].key === 'jelentes' && Array.isArray(helyesErtek)) {
                                                // Jelentés mezőknél a teljes listát kiírjuk
                                                helyesText = helyesErtek.join(', ');
                                            } else if (Array.isArray(helyesErtek)) {
                                                helyesText = helyesErtek.join(', ');
                                            } else {
                                                helyesText = helyesErtek;
                                            }
                                            
                                            const helyesDiv = document.createElement('div');
                                            helyesDiv.className = 'correct-answer';
                                            helyesDiv.textContent = `Helyes: ${helyesText}`;
                                            helyesDiv.style.color = 'green';
                                            helyesDiv.style.fontSize = '0.9em';
                                            helyesDiv.style.marginTop = '2px';
                                            select.parentElement.appendChild(helyesDiv);
                                        }
                                    }
                                }
                            }
                        } else if (result.status === 'próbálkozás') {
                            if (helyes) {
                                select.classList.add('input-correct');
                                select.disabled = true;
                            } else {
                                // Próbálkozásnál hibás mező: csak piros betűszín, mindig szerkeszthető marad
                                select.classList.add('input-error-text');
                            }
                        }
                    }
                }
            }
        }
        
        // Próbálkozások számának frissítése
        const probalkozasDiv = container.querySelector('.task-attempts');
        if (probalkozasDiv && typeof result.probalkozasok_szama !== 'undefined') {
            probalkozasDiv.textContent = `Próbálkozás: ${result.probalkozasok_szama} / ${allapot.max_probalkozas}`;
        }
        
        // Gombok kezelése eredmény alapján
        const btnGroup = container.querySelector('.btn-group');
        if (btnGroup) {
            btnGroup.innerHTML = '';
            
            if (result.status === 'beküldve') {
                // Gombok cseréje "Következő feladat" gombra
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
                // Próbálkozás után újra kell kötni az eseménykezelőket
                const newSubmitBtn = document.createElement('button');
                newSubmitBtn.type = 'button';
                newSubmitBtn.textContent = 'Beküldés';
                btnGroup.appendChild(newSubmitBtn);
                const newTryBtn = document.createElement('button');
                newTryBtn.type = 'button';
                newTryBtn.textContent = 'Próbálkozás';
                btnGroup.appendChild(newTryBtn);
                
                // Újra kell kötni az eseménykezelőket
                newSubmitBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (!validateInputs()) return;
                    const answers = collectAnswers();
                    // Tároljuk a variacioSzam-t a containerben
                    container.dataset.variacioSzam = variacioSzam;
                    if (typeof onSubmit === 'function') {
                        onSubmit({ task_id, answers, probalkozas: false, variacioSzam });
                    }
                });
                newTryBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (!validateInputs()) return;
                    const answers = collectAnswers();
                    // Tároljuk a variacioSzam-t a containerben
                    container.dataset.variacioSzam = variacioSzam;
                    if (typeof onSubmit === 'function') {
                        onSubmit({ task_id, answers, probalkozas: true, variacioSzam });
                    }
                });
            }
        }
    }
    
    // Validációs logika (result esetén is elérhető)
    function validateInputs() {
        const table = container.querySelector('.parositasos-table');
        if (!table) return true;
        
        let valid = true;
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach((row, i) => {
            const selects = row.querySelectorAll('select');
            selects.forEach((select, c) => {
                if (!select.value && select.value !== '0') {
                    valid = false;
                    select.classList.add('input-error');
                } else {
                    select.classList.remove('input-error');
                }
            });
        });
        
        const errorDiv = container.querySelector('.task-error');
        if (errorDiv) {
            if (!valid) {
                errorDiv.textContent = 'Minden mezőhöz válassz ki egy lehetőséget!';
                errorDiv.style.display = 'block';
            } else {
                errorDiv.style.display = 'none';
            }
        }
        return valid;
    }

    // Válaszok összegyűjtése (result esetén is elérhető)
    function collectAnswers() {
        const table = container.querySelector('.parositasos-table');
        if (!table) return {};
        
        const answers = {};
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach((row, i) => {
            const selects = row.querySelectorAll('select');
            selects.forEach((select, c) => {
                const colKey = columns[c].key;
                if (!answers[colKey]) {
                    answers[colKey] = [];
                }
                const val = select.value;
                answers[colKey].push(val === '' ? null : parseInt(val, 10));
            });
        });
        
        // Egy elemű listák egyszerűsítése
        for (let c = 0; c < columns.length; c++) {
            const col = columns[c];
            if (answers[col.key] && answers[col.key].length === 1) {
                answers[col.key] = [answers[col.key][0]];
            }
        }
        
        return answers;
    }
}
