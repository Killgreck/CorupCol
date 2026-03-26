/**
 * Módulo de Referencia de Periodos Políticos
 * Contiene datos estáticos para contextualizar los hallazgos de contratación
 * por presidente, gobernador y alcalde en periodos específicos.
 */

const periodosPoliticos = {
    // Presidentes de la República (2000 - 2026)
    presidentes: [
        { id: "pastrana", nombre: "Andrés Pastrana Arango", inicio: "1998-08-07", fin: "2002-08-07" },
        { id: "uribe1", nombre: "Álvaro Uribe Vélez (I)", inicio: "2002-08-07", fin: "2006-08-07" },
        { id: "uribe2", nombre: "Álvaro Uribe Vélez (II)", inicio: "2006-08-07", fin: "2010-08-07" },
        { id: "santos1", nombre: "Juan Manuel Santos (I)", inicio: "2010-08-07", fin: "2014-08-07" },
        { id: "santos2", nombre: "Juan Manuel Santos (II)", inicio: "2014-08-07", fin: "2018-08-07" },
        { id: "duque", nombre: "Iván Duque Márquez", inicio: "2018-08-07", fin: "2022-08-07" },
        { id: "petro", nombre: "Gustavo Petro Urrego", inicio: "2022-08-07", fin: "2026-08-07" }
    ],

    // Gobernadores de los principales departamentos (Últimos 3 periodos: 2016-2027)
    // Se incluyen los departamentos con mayor presupuesto/población
    gobernadores: {
        "Antioquia": [
            { id: "ant_2016", nombre: "Luis Pérez Gutiérrez", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "ant_2020", nombre: "Aníbal Gaviria Correa", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "ant_2024", nombre: "Andrés Julián Rendón", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Atlántico": [
            { id: "atl_2016", nombre: "Eduardo Verano de la Rosa", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "atl_2020", nombre: "Elsa Noguera", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "atl_2024", nombre: "Eduardo Verano de la Rosa", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Bogotá D.C.": [
            { id: "bog_2016", nombre: "Enrique Peñalosa (Alcalde Mayor)", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "bog_2020", nombre: "Claudia López (Alcaldesa Mayor)", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "bog_2024", nombre: "Carlos Fernando Galán (Alcalde Mayor)", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Bolívar": [
            { id: "bol_2016", nombre: "Dumek Turbay Paz", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "bol_2020", nombre: "Vicente Antonio Blel", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "bol_2024", nombre: "Yamil Arana", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Boyacá": [
            { id: "boy_2016", nombre: "Carlos Andrés Amaya", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "boy_2020", nombre: "Ramiro Barragán Adame", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "boy_2024", nombre: "Carlos Andrés Amaya", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Caldas": [
            { id: "cal_2016", nombre: "Guido Echeverri / Julián Gutiérrez", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cal_2020", nombre: "Luis Carlos Velásquez", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cal_2024", nombre: "Henry Gutiérrez Ángel", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Cauca": [
            { id: "cau_2016", nombre: "Óscar Rodrigo Campo", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cau_2020", nombre: "Elías Larrahondo Carabalí", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cau_2024", nombre: "Octavio Guzmán", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Cesar": [
            { id: "ces_2016", nombre: "Francisco Ovalle Angarita", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "ces_2020", nombre: "Luis Alberto Monsalvo Gnecco", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "ces_2024", nombre: "Elvia Milena Sanjuan", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Córdoba": [
            { id: "cor_2016", nombre: "Edwin Besaile (Suspendido) / Sandra Devia", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cor_2020", nombre: "Orlando Benítez Mora", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cor_2024", nombre: "Erasmo Zuleta Bechara", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Cundinamarca": [
            { id: "cun_2016", nombre: "Jorge Emilio Rey", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cun_2020", nombre: "Nicolás García Bustos", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cun_2024", nombre: "Jorge Emilio Rey", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Chocó": [
            { id: "cho_2016", nombre: "Jhoany Carlos Alberto Palacios", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cho_2020", nombre: "Ariel Palacios Calderón", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cho_2024", nombre: "Nubia Carolina Córdoba", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Huila": [
            { id: "hui_2016", nombre: "Carlos Julio González Villa", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "hui_2020", nombre: "Luis Enrique Dussán", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "hui_2024", nombre: "Rodrigo Villalba Mosquera", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "La Guajira": [
            { id: "gua_2016", nombre: "Oneida Pinto / Wilmer González / Tania Buitrago", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "gua_2020", nombre: "Nemesio Roys Garzón", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "gua_2024", nombre: "Jairo Aguilar Deluque", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Magdalena": [
            { id: "mag_2016", nombre: "Rosa Cotes de Zúñiga", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "mag_2020", nombre: "Carlos Caicedo / Rafael Martínez", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "mag_2024", nombre: "Rafael Martínez", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Meta": [
            { id: "met_2016", nombre: "Marcela Amaya", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "met_2020", nombre: "Juan Guillermo Zuluaga", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "met_2024", nombre: "Rafaela Cortés Zambrano", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Nariño": [
            { id: "nar_2016", nombre: "Camilo Romero", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "nar_2020", nombre: "Jhon Rojas Cabrera", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "nar_2024", nombre: "Luis Alfonso Escobar", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Norte de Santander": [
            { id: "nds_2016", nombre: "William Villamizar Laguado", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "nds_2020", nombre: "Silvano Serrano Guerrero", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "nds_2024", nombre: "William Villamizar Laguado", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Quindío": [
            { id: "qui_2016", nombre: "Carlos Eduardo Osorio", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "qui_2020", nombre: "Roberto Jairo Jaramillo", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "qui_2024", nombre: "Juan Miguel Galvis Bedoya", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Risaralda": [
            { id: "ris_2016", nombre: "Sigifredo Salazar Osorio", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "ris_2020", nombre: "Víctor Manuel Tamayo", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "ris_2024", nombre: "Juan Diego Patiño Ochoa", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Santander": [
            { id: "san_2016", nombre: "Didier Tavera Amado", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "san_2020", nombre: "Mauricio Aguilar Hurtado", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "san_2024", nombre: "Juvenal Díaz Mateus", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Sucre": [
            { id: "suc_2016", nombre: "Edgar Martínez Romero", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "suc_2020", nombre: "Héctor Olimpo Espinosa", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "suc_2024", nombre: "Lucy García Montes", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Tolima": [
            { id: "tol_2016", nombre: "Óscar Barreto Quiroga", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "tol_2020", nombre: "Ricardo Orozco Valero", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "tol_2024", nombre: "Adriana Magali Matiz", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Valle del Cauca": [
            { id: "val_2016", nombre: "Dilian Francisca Toro", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "val_2020", nombre: "Clara Luz Roldán", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "val_2024", nombre: "Dilian Francisca Toro", inicio: "2024-01-01", fin: "2027-12-31" }
        ]
    },

    // Alcaldes de Ciudades Principales (Últimos 3 periodos: 2016-2027)
    alcaldes: {
        "Bogotá": [
            { id: "bog_a_2016", nombre: "Enrique Peñalosa Londoño", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "bog_a_2020", nombre: "Claudia López Hernández", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "bog_a_2024", nombre: "Carlos Fernando Galán", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Medellín": [
            { id: "med_2016", nombre: "Federico Gutiérrez", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "med_2020", nombre: "Daniel Quintero Calle", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "med_2024", nombre: "Federico Gutiérrez", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Cali": [
            { id: "cal_a_2016", nombre: "Maurice Armitage", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cal_a_2020", nombre: "Jorge Iván Ospina", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cal_a_2024", nombre: "Alejandro Eder", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Barranquilla": [
            { id: "bar_2016", nombre: "Alejandro Char", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "bar_2020", nombre: "Jaime Pumarejo", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "bar_2024", nombre: "Alejandro Char", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Cartagena": [
            { id: "ctg_2016", nombre: "Manolo Duque (Suspendido) / Pedrito Pereira", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "ctg_2020", nombre: "William Dau Chamat", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "ctg_2024", nombre: "Dumek Turbay Paz", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Bucaramanga": [
            { id: "buc_2016", nombre: "Rodolfo Hernández Suárez", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "buc_2020", nombre: "Juan Carlos Cárdenas", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "buc_2024", nombre: "Jaime Andrés Beltrán", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Cúcuta": [
            { id: "cuc_2016", nombre: "César Rojas Ayala", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "cuc_2020", nombre: "Jairo Tomás Yáñez", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "cuc_2024", nombre: "Jorge Acevedo Peñaloza", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Montería": [
            { id: "mon_2016", nombre: "Marcos Daniel Pineda", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "mon_2020", nombre: "Carlos Ordosgoitia", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "mon_2024", nombre: "Hugo Kerguelén", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Valledupar": [
            { id: "val_2016", nombre: "Augusto Ramírez Uhía", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "val_2020", nombre: "Mello Castro", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "val_2024", nombre: "Ernesto Orozco", inicio: "2024-01-01", fin: "2027-12-31" }
        ],
        "Villavicencio": [
            { id: "vil_2016", nombre: "Wilmar Barbosa", inicio: "2016-01-01", fin: "2019-12-31" },
            { id: "vil_2020", nombre: "Felipe Harman", inicio: "2020-01-01", fin: "2023-12-31" },
            { id: "vil_2024", nombre: "Alexander Baquero", inicio: "2024-01-01", fin: "2027-12-31" }
        ]
    }
};

// Utilidades para buscar periodos según fecha
const politicosUtils = {
    /**
     * Devuelve el presidente en el cargo para una fecha dada
     * @param {string} fechaStr - Fecha en formato YYYY-MM-DD
     * @returns {object|null} Objeto presidente o null
     */
    getPresidenteByDate(fechaStr) {
        if (!fechaStr) return null;
        const targetDate = new Date(fechaStr);
        return periodosPoliticos.presidentes.find(p => {
            return targetDate >= new Date(p.inicio) && targetDate <= new Date(p.fin);
        }) || null;
    },

    /**
     * Devuelve el gobernador para un departamento y fecha
     * @param {string} depto - Nombre del departamento
     * @param {string} fechaStr - Fecha en formato YYYY-MM-DD
     * @returns {object|null} Objeto gobernador o null
     */
    getGobernadorByDate(depto, fechaStr) {
        if (!fechaStr || !depto || !periodosPoliticos.gobernadores[depto]) return null;
        const targetDate = new Date(fechaStr);
        return periodosPoliticos.gobernadores[depto].find(g => {
            return targetDate >= new Date(g.inicio) && targetDate <= new Date(g.fin);
        }) || null;
    },

    /**
     * Devuelve el alcalde para una ciudad y fecha
     * @param {string} ciudad - Nombre de la ciudad
     * @param {string} fechaStr - Fecha en formato YYYY-MM-DD
     * @returns {object|null} Objeto alcalde o null
     */
    getAlcaldeByDate(ciudad, fechaStr) {
        if (!fechaStr || !ciudad || !periodosPoliticos.alcaldes[ciudad]) return null;
        const targetDate = new Date(fechaStr);
        return periodosPoliticos.alcaldes[ciudad].find(a => {
            return targetDate >= new Date(a.inicio) && targetDate <= new Date(a.fin);
        }) || null;
    },

    /**
     * Filtra un arreglo de datos basándose en el campo de fecha y el rango
     * @param {Array} data - Arreglo de objetos a filtrar
     * @param {string} dateField - Nombre del campo de fecha en los objetos
     * @param {string} inicio - Fecha de inicio (YYYY-MM-DD)
     * @param {string} fin - Fecha de fin (YYYY-MM-DD)
     * @returns {Array} Arreglo filtrado
     */
    filterByPeriodo(data, dateField, inicio, fin) {
        if (!inicio && !fin) return data;

        const startDate = inicio ? new Date(inicio) : new Date('1990-01-01');
        const endDate = fin ? new Date(fin) : new Date('2050-01-01');

        return data.filter(item => {
            const itemDate = item[dateField] ? new Date(item[dateField]) : null;
            if (!itemDate || isNaN(itemDate.getTime())) return true; // Si no tiene fecha válida, lo mantenemos por si acaso o false, decidimos true
            return itemDate >= startDate && itemDate <= endDate;
        });
    }
};
