import random
import pickle
import logging
import argparse
import numpy as np
import configparser

from fitness import Fitness
from config import instance, concept_coverage, objectives, num_students, num_concepts, num_materials, recommendation, dir

class Grasp:
  def __init__(self, max_iterations, local_search_size, alpha_m, alpha_c, max_materials_changes, max_concepts_changes, seed):
    self.max_iterations = max_iterations
    self.local_search_size = local_search_size
    self.alpha_m = alpha_m
    self.alpha_c = alpha_c
    self.max_materials_changes = max_materials_changes
    self.max_concepts_changes = max_concepts_changes
    self.seed = seed
  
  @classmethod
  def from_config(cls, config_filename):
    config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    config.read(config_filename)
    
    max_iterations = int(config['default']['max_iterations'])
    local_search_size = int(config['default']['local_search_size'])
    alpha_m = float(config['default']['alpha_m'])
    alpha_c = float(config['default']['alpha_c'])
    max_materials_changes = float(config['default']['max_materials_changes'])
    max_concepts_changes = float(config['default']['max_concepts_changes'])
    seed = int(config['default']['seed'])
    
    return cls(max_iterations, local_search_size, alpha_m, alpha_c, max_materials_changes, max_concepts_changes, seed)
  
  
  def run(self, concept_coverage, fitnessConcepts_total, DATFILE=None):
    best_solution = concept_coverage
    best_fitness = fitnessConcepts_total
    
    fitness_progress = np.empty(self.max_iterations)
    for i in range(self.max_iterations):
      solution, solution_fitness, materials_changed = self.greadyRandomizedConstruction()
      #if(!isFeasible(solution)):
      solution, solution_fitness = self.localSearch(solution, solution_fitness, materials_changed)
      
      if(solution_fitness < best_fitness):
        best_solution = solution
        best_fitness = solution_fitness
      
      fitness_progress[i] = best_fitness
      
    if(DATFILE):
      with open(DATFILE, 'w') as f:
        f.write(str(best_fitness))
    else:
      with open('results_grasp.pickle', 'wb') as file:
        pickle.dump({"fitness_progress": fitness_progress, "grasp_concept_coverage": best_solution, "grasp_fitness": best_fitness}, file)
      
      return best_solution, best_fitness
  
  
  def greadyRandomizedConstruction(self):
    student_yes = np.matmul(recommendation.astype(int), objectives.astype(int)) #quantos alunos receberam o material E o tem como objetivo
    student_no = np.matmul(recommendation.astype(int), (~objectives).astype(int)) #quantos alunos receberam o material E não o tem como objetivo
    student_difference = student_no - student_yes #(quantos alunos querem ter o conveito adicionado) - (quantos alunos querem ter o conceito removido)
    scaled_coverage = (concept_coverage * 2 - 1) # concept_coverage, onde False é -1 e True é 1
    conflicts = student_difference * scaled_coverage
    change_potential = np.maximum(0, conflicts).sum(axis=1)
    
    materials_changed = []
    new_concept_coverage = concept_coverage.copy()
    change_potential_order = np.argsort(-change_potential).tolist()
    
    for j in range(int(self.max_materials_changes * num_materials)):
        # Select a material and remove from the list
        selected_material_index = random.randrange(int(len(change_potential_order) * self.alpha_m))
        material = change_potential_order[selected_material_index]
        materials_changed.append(material)
        del change_potential_order[selected_material_index]

        # print('[', material, change_potential[material], ']')
        # print(conflicts[material])

        conflicts_order = np.argsort(-conflicts[material]).tolist()
        for k in range(int(self.max_concepts_changes * num_concepts)):
            # Select a concept from the material and remove from the list
            selected_concept_index = random.randrange(int(len(conflicts_order) * self.alpha_c))
            concept = conflicts_order[selected_concept_index]
            del conflicts_order[selected_concept_index]

            # print(material, concept)
            if conflicts[material, concept] > 0:
                new_concept_coverage[material, concept] = ~new_concept_coverage[material, concept]

    new_best_fitness = sum([Fitness.get_fitnessConcepts(student_id, new_concept_coverage.T) for student_id in range(num_students)])/num_students
    return new_concept_coverage, new_best_fitness, materials_changed
  
  
  def localSearch(self, solution, solution_fitness, materials_changed):
    new_concept_coverage = solution
    new_best_fitness = solution_fitness
    
    for j in range(self.local_search_size):
        fitness_improved = False
        for material in materials_changed:
            for concept in range(num_concepts):
                step_concept_coverage = new_concept_coverage.copy()
                step_concept_coverage[material, concept] = ~step_concept_coverage[material, concept]
                step_fitness = sum([Fitness.get_fitnessConcepts(student_id, step_concept_coverage.T) for student_id in range(num_students)])/num_students

                if new_best_fitness > step_fitness:
                    new_best_fitness = step_fitness
                    new_concept_coverage = step_concept_coverage
                    fitness_improved = True

        if not fitness_improved:
            break
    return new_concept_coverage, new_best_fitness
  

  def __repr__(self):
    return f'\n max_iterations: {self.max_iterations}\n local_search_size: {self.local_search_size}\n alpha_m: {self.alpha_m}\n alpha_c: {self.alpha_c}\n max_materials_changes: {self.max_materials_changes}\n max_concepts_changes: {self.max_concepts_changes}\n seed: {self.seed}\n'
  
if __name__ == '__main__':
  ap = argparse.ArgumentParser(description='Feature Selection using GA with DecisionTreeClassifier')
  ap.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
  ap.add_argument('--max_iterations', type=int, default=100, help='Number of iterations')
  ap.add_argument('--local_search_size', type=int, default=2, help='Number of iterations in local search')
  ap.add_argument('--alpha_m', type=float, default=0.2, help='alpha of materials')
  ap.add_argument('--alpha_c', type=float, default=0.3, help='alpha of concepts')
  ap.add_argument('--datfile', dest='datfile', type=str, help='File where it will be save the score (result)')

  args = ap.parse_args()

  if args.verbose:
      logging.basicConfig(level=logging.DEBUG)

  logging.debug(args)
  
  student_results_before = sum([Fitness.get_fitnessConcepts(student_id, concept_coverage.T) for student_id in range(num_students)])/num_students
  
  grasp = Grasp(args.max_iterations, args.local_search_size, args.alpha_m, args.alpha_c, 0.0356, 0.1667, 98092891)
  
  grasp.run(concept_coverage, student_results_before, args.datfile)
  # grasp_concept_coverage, student_results_grasp = grasp.run(concept_coverage, student_results_before)
  # print(f'student_results_grasp: {student_results_grasp}')