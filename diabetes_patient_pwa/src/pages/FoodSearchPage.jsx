import React, { useState } from 'react';
import {
    Grid,
    Typography,
    Paper,
    CircularProgress,
    TableContainer,
    Table,
    TableHead,
    TableRow,
    TableCell,
    TableBody
} from '@mui/material';
import {
    PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend
} from 'recharts';
import FoodSearchBar from '../components/FoodSearchBar';
import { COLORS } from '../constants/colors';

const FoodSearchPage = () => {
  const [selectedFood, setSelectedFood] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFoodSelect = (food) => {
    setLoading(true);
    // Simulate API fetch delay
    setTimeout(() => {
      setSelectedFood(food);
      setLoading(false);
    }, 500);
  };

  const prepareChartData = () => {
    if (!selectedFood) return [];
    
    return [
      { name: 'Πρωτεΐνες', value: parseFloat(selectedFood.proteins) },
      { name: 'Υδατάνθρακες', value: parseFloat(selectedFood.Carbonhydrates) },
      { name: 'Λιπαρά', value: parseFloat(selectedFood.fats) }
    ];
  };


  return (
    <Grid container spacing={3} sx={{ p: 3 }}>
      <Grid item xs={12}>
        <Typography variant="h4" gutterBottom>
          Αναζήτηση Τροφής
        </Typography>
        <FoodSearchBar onSelect={handleFoodSelect} />
      </Grid>

      {loading && (
        <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress size={60} />
        </Grid>
      )}

      {selectedFood && !loading && (
        <>
          <Grid item xs={12}>
            <Paper elevation={3} sx={{ p: 2, height: 550, minWidth: 700, mb: 3 }}>
                <Typography variant="h6" gutterBottom align="center">
                    Μακροθρεπτικά Συστατικά
                </Typography>
                <ResponsiveContainer width="100%" height="95%">
                    <PieChart>
                        <Pie
                            data={prepareChartData()}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={180}
                            fill="#8884d8"
                            dataKey="value"
                            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        >
                            {prepareChartData().map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip formatter={(value) => [`${value}g`, 'Ποσότητα']} />
                        <Legend />
                    </PieChart>
                </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12}>
            <Paper elevation={3} sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                {selectedFood.category}
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Στοιχείο</TableCell>
                      <TableCell align="right">Ποσότητα</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                   <TableRow>
                     <TableCell>Θερμίδες</TableCell>
                     <TableCell align="right">{selectedFood.calories || 'N/A'} kcal</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Φυτικές Ίνες</TableCell>
                     <TableCell align="right">{selectedFood.fibers || 'N/A'}g</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Σάκχαρα</TableCell>
                     <TableCell align="right">{selectedFood.sugars || 'N/A'}g</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Χοληστερόλη</TableCell>
                     <TableCell align="right">{selectedFood.cholesterol || 'N/A'}mg</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Βιταμίνη Α</TableCell>
                     <TableCell align="right">{selectedFood.vitaminA || 'N/A'}μg</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Βιταμίνη C</TableCell>
                     <TableCell align="right">{selectedFood.vitaminC || 'N/A'}mg</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Ασβέστιο</TableCell>
                     <TableCell align="right">{selectedFood.calcium || 'N/A'}mg</TableCell>
                   </TableRow>
                   <TableRow>
                     <TableCell>Σίδηρος</TableCell>
                     <TableCell align="right">{selectedFood.iron || 'N/A'}mg</TableCell>
                   </TableRow>
                 </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

export default FoodSearchPage;