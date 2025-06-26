import { fetchUtils } from 'react-admin';
import simpleRestProvider from 'ra-data-simple-rest';

const httpClient = (url, options = {}) => {
  // Προσθέτουμε το JWT token από το localStorage στο Authorization header
  const token = localStorage.getItem('access_token');
  if (token) {
    options.headers = new Headers({ 
      Accept: 'application/json', // Προσθέτουμε Accept header
      Authorization: `Bearer ${token}`, 
      ...(options.headers || {}), // Διατηρούμε τυχόν υπάρχοντα headers
    });
  } else {
    options.headers = new Headers({ 
      Accept: 'application/json',
      ...(options.headers || {}), 
    });
  }
  console.log(`Fetching: ${url}`, options); // Debug log

  // Ελέγχουμε αν το URL είναι για /patients/{id} ή /doctors/{id}
  const idPattern = /\/(patients|doctors)\/([^\/]+)$/;
  const match = url.match(idPattern);
  
  if (match) {
    const resource = match[1];
    const id = match[2];
    
    return fetchUtils.fetchJson(url, options)
      .catch((error) => {
        console.error('Fetch Error:', error); // Debug log για σφάλματα
        
        // Αν είναι 403 και είμαστε σε GET για patients ή doctors
        if (error.status === 403 && options.method === 'GET') {
          console.log(`Converting 403 to empty response for ${resource}/${id}`);
          
          // Επιστρέφουμε ένα κενό object αντί να απορρίψουμε το Promise
          return { json: { id: id, message: 'Access Restricted' } };
        }
        
        return Promise.reject(error);
      });
  }
  
  return fetchUtils.fetchJson(url, options)
    .catch((error) => {
      console.error('Fetch Error:', error); // Debug log για σφάλματα
      return Promise.reject(error);
    });
};

// Ορίζουμε το βασικό URL του backend API
const apiUrl = 'http://localhost:5000/api';

// Αρχικοποιούμε τον provider
const baseDataProvider = simpleRestProvider(apiUrl, httpClient);

// Κάνουμε override τη μέθοδο update για να χρησιμοποιεί PATCH αντί για PUT
export const dataProvider = {
    ...baseDataProvider, // Κληρονομούμε όλες τις άλλες μεθόδους
    
    // Ειδικός χειρισμός για το doctor-portal/patients
    getList: (resource, params) => {
        // Αν είναι το doctor-portal/patients, χρησιμοποιούμε ειδικό χειρισμό
        if (resource === 'doctor-portal/patients') {
            console.log(`[dataProvider] Special handling for ${resource}`);
            
            // Δημιουργία παραμέτρων για το URL
            const { page, perPage } = params.pagination;
            const { field, order } = params.sort;
            
            // Δημιουργία ερωτήματος για το URL
            const query = {
                filter: JSON.stringify(params.filter),
                sort: JSON.stringify([field, order]),
                range: JSON.stringify([(page - 1) * perPage, page * perPage - 1]),
            };
            
            const url = `${apiUrl}/${resource}?${Object.keys(query).map(key => 
                `${encodeURIComponent(key)}=${encodeURIComponent(query[key])}`
            ).join('&')}`;
            
            return httpClient(url)
                .then(({ json }) => {
                    // Αν το backend δεν επιστρέφει Content-Range header, το προσθέτουμε εμείς
                    return {
                        data: json.map(record => ({ ...record, id: record._id || record.id })),
                        total: json.length, // Υποθέτουμε ότι επιστρέφει όλα τα αποτελέσματα
                    };
                });
        }
        
        // Για άλλους πόρους, χρησιμοποιούμε την default υλοποίηση
        return baseDataProvider.getList(resource, params);
    },
    
    // Override getOne για να χειριστεί ειδικά τα 403 σφάλματα
    getOne: (resource, params) => {
        // Αν ζητάμε ένα από το 'doctor-portal/patients', στην πραγματικότητα θέλουμε από το 'patients'
        if (resource === 'doctor-portal/patients') {
             console.log(`[dataProvider] Rerouting getOne from ${resource} to patients for id: ${params.id}`);
             // Καλούμε απευθείας το httpClient με το σωστό URL
            const url = `${apiUrl}/patients/${params.id}`;
            return httpClient(url).then(({ json }) => ({ data: json }));
        }
        // Αλλιώς, καλούμε την default υλοποίηση
        return baseDataProvider.getOne(resource, params);
    },
    
    // Προαιρετικά: Μπορούμε να κάνουμε το ίδιο και για update/delete αν χρειαστεί
    update: (resource, params) => {
        if (resource === 'doctor-portal/patients') {
            console.log(`[dataProvider] Rerouting update from ${resource} to patients for id: ${params.id}`);
             // Καλούμε απευθείας το httpClient με το σωστό URL και μέθοδο PATCH
            const url = `${apiUrl}/patients/${params.id}`;
             return httpClient(url, {
                 method: 'PATCH',
                 body: JSON.stringify(params.data),
                 // Η απάντηση από /api/patients/<id> (update_patient) είναι ήδη { data: ... }
             }).then(({ json }) => (json)); 
        }
        // Διατηρούμε την προηγούμενη υπερκάλυψη για PATCH για τους άλλους πόρους
        console.log(`[dataProvider] Default update for ${resource} using PATCH`);
        return httpClient(`${apiUrl}/${resource}/${params.id}`, {
            method: 'PATCH', 
            body: JSON.stringify(params.data),
        // Διόρθωση: Επιστρέφουμε απευθείας το json γιατί περιέχει ήδη το { data: ... }
        }).then(({ json }) => (json)); 
    },
    
    // Override create για να τυλίξει την απάντηση σε { data: ... }
    create: (resource, params) => {
        const url = `${apiUrl}/${resource}`;
        return httpClient(url, {
            method: 'POST',
            body: JSON.stringify(params.data),
        }).then(({ json }) => {
            // Τυλίγουμε το αποτέλεσμα (το record) μέσα σε ένα object με κλειδί 'data'
            console.log("[dataProvider create] Wrapping response in { data: ... }:", json);
            return { data: json }; 
        });
    },
    
    delete: (resource, params) => {
        if (resource === 'doctor-portal/patients') {
             console.log(`[dataProvider] Rerouting delete from ${resource} to patients for id: ${params.id}`);
             // Καλούμε απευθείας το httpClient με το σωστό URL και μέθοδο DELETE
            const url = `${apiUrl}/patients/${params.id}`;
            return httpClient(url, {
                method: 'DELETE',
            }).then(({ json }) => ({ data: json })); // Το react-admin περιμένει το record που διαγράφηκε
        }
        return baseDataProvider.delete(resource, params);
    },
    deleteMany: (resource, params) => {
         if (resource === 'doctor-portal/patients') {
            console.log(`[dataProvider] Rerouting deleteMany from ${resource} to patients for ids: ${params.ids}`);
             // Για το deleteMany, το baseDataProvider συνήθως κάνει πολλαπλές κλήσεις delete
             // Η πιο απλή προσέγγιση είναι να καλέσουμε το baseDataProvider με το σωστό resource
             return baseDataProvider.deleteMany('patients', params);
         }
         return baseDataProvider.deleteMany(resource, params);
    },
};

// Προαιρετικά: Μπορούμε να κάνουμε override συγκεκριμένες μεθόδους αν χρειάζεται
// π.χ., αν το endpoint για τους ασθενείς του γιατρού είναι διαφορετικό
// const myDataProvider = {
//   ...dataProvider,
//   getList: (resource, params) => {
//     if (resource === 'doctor-patients') { // Ένα παράδειγμα για ειδικό endpoint
//       const url = `${apiUrl}/doctor-portal/patients`; 
//       return httpClient(url).then(({ json }) => ({
//         data: json,
//         total: json.length, // Υποθέτουμε ότι το API επιστρέφει απευθείας τη λίστα
//       }));
//     }
//     // Για άλλους πόρους, χρησιμοποιούμε την default υλοποίηση
//     return dataProvider.getList(resource, params);
//   },
// };

// export { myDataProvider as dataProvider }; // Αν κάνουμε override 