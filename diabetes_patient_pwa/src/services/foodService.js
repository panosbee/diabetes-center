import greekFoodData from '../../greek.json';

export const searchFoods = (query) => {
  return greekFoodData.filter(food => 
    food.category.toLowerCase().includes(query.toLowerCase())
  );
};

export const getFoodById = (id) => {
  return greekFoodData.find(food => food.id === id);
};