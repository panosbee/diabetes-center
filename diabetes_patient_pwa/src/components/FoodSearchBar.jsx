import React, { useState, useEffect } from 'react';
import { 
  TextField, 
  Autocomplete, 
  InputAdornment,
  ListItem,
  ListItemText,
  useMediaQuery 
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { searchFoods } from '../services/foodService';

const FoodSearchBar = ({ onSelect }) => {
  const [inputValue, setInputValue] = useState('');
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const isMobile = useMediaQuery('(max-width:600px)');

  // Debounced search
  useEffect(() => {
    if (inputValue.length < 2) {
      setOptions([]);
      return;
    }

    setLoading(true);
    const timer = setTimeout(() => {
      const results = searchFoods(inputValue);
      setOptions(results);
      setLoading(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [inputValue]);

  return (
    <Autocomplete
      freeSolo
      disableClearable
      options={options}
      loading={loading}
      getOptionLabel={(option) => option.category || ''}
      onChange={(_, value) => value && onSelect(value)}
      renderInput={(params) => (
        <TextField
          {...params}
          variant="outlined"
          placeholder="Αναζήτηση τροφής..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          InputProps={{
            ...params.InputProps,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{
            minWidth: isMobile ? '100%' : 400,
            backgroundColor: 'white',
            borderRadius: 2
          }}
        />
      )}
      renderOption={(props, option) => (
        <ListItem {...props} key={option.id}>
          <ListItemText primary={option.category} />
        </ListItem>
      )}
    />
  );
};

export default FoodSearchBar;