"""
Bot responsável por obter as notas dos desafios dos participantes de algum programa de
empregabilidade. Ele já cadastra as notas dos desafios gerados pela plataforma Coderbyte
no sistema Externo.
"""
import argparse
import itertools
import sys
from typing import List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector

CODERBYTE_URL = "https://coderbyte.com/sl-org"
USERNAME = "william.cirico@proway.com.br"
PASSWORD = "X*&ricr6*LS4"

def remove_duplicates(scores: List[Tuple[float, str]]) -> List[Tuple[float, str]]:
    new_data = {}
    for score, email in scores:
        if email not in new_data or score >= new_data[email]:
            new_data[email] = score
            
    return [(new_data[email], email) for email in new_data]


def format_score(score: str) -> float:
    """Formats the score in '%d' format to float"""
    return float(score.replace("%", ""))

def calculate_final_score(multiple_choice_scores: List[float], code_scores: List[float], multiple_choice_weight: float, code_weight: float) -> List[float]:
    """Calculates the final score of tests based on the weight of the constants """
    final_scores = []
    for (multiple_choice_score, code_score) in zip(multiple_choice_scores, code_scores):
        final_score = (multiple_choice_score * multiple_choice_weight + code_score * code_weight) / (code_weight + multiple_choice_weight)
        final_scores.append(final_score)

    return final_scores


def get_scores_from_assesment(driver: any, assesmentURL: str, multiple_choice_weight: float, code_weight: float, status: str = "submitted") -> List[Tuple[float, str]]:
    """Returns the scores from an acessment"""
    driver.get(assesmentURL)

    # Obtendo os e-mails e scores
    if status == "submitted" or status == None:
        emails_elements = driver.find_elements(By.XPATH, "//span[contains(., 'Submitted')]/preceding-sibling::span[1]")
        scores_elements = driver.find_elements(By.XPATH, "//span[contains(., 'Submitted')]/following-sibling::span[contains(@class, 'score')]")
    elif status == "all":    
        emails_elements = driver.find_elements(By.CSS_SELECTOR, ".candidateRow > span:nth-child(2)")
        scores_elements = driver.find_elements(By.CLASS_NAME, "score")

    # Obtendo o score das questões de múltipla escolha
    driver.find_element(By.XPATH, "//option[@value='mc_score']").click()
    multiple_choice_scores = list(map(lambda score: format_score(score.text), scores_elements))

    # Obtendo o score dos desafios de programação
    driver.find_element(By.XPATH, "//option[@value='code_score']").click()    
    code_scores = list(map(lambda score: format_score(score.text), scores_elements))

    # Obtendo o score final
    final_scores = calculate_final_score(multiple_choice_scores, code_scores, multiple_choice_weight, code_weight)

    # Obtendo os emails
    emails = list(map(lambda email: email.text, emails_elements))

    return list(zip(final_scores, emails))

    

def get_links_from_assessment(driver: any, assessment_url: str, assessment_name: str) -> List[str]:
    """Get all the sumitted assesments from an URL"""    
    driver.get(assessment_url)

    # Realizando o login
    driver.find_element(By.CLASS_NAME, "login-field-input").send_keys(USERNAME)
    driver.find_element(By.CLASS_NAME, "nextButton").click()    
    wait = WebDriverWait(driver, 10)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))).send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[text()='Log in']").click()    

    # Navegando para a página de avaliações
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Assessments"))).click()
    
    # Localizando os links dos desafios
    assesments_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, f"//h3[contains(., '{assessment_name}')]/following-sibling::a[1]")))
    
    # Obtendo os links
    links = list(map(lambda x: x.get_attribute("href"), assesments_links))

    return links


def save_challenges_in_db(assessments_scores: List[Tuple[float, str]], project_id: int):
    """Saves the scores from an assesment in the DB"""
    try:
        with mysql.connector.connect(
            host="localhost",
        user="root",
        password="",
        database="empregabilidade_homologacao"
        ) as connection:
            with connection.cursor() as cursor:            
                sql = f"UPDATE inscritos SET nota_teste = %s WHERE email = %s AND projeto_id = {project_id}"

                for assessment_score in assessments_scores:                    
                    cursor.execute(sql, assessment_score)
                
                connection.commit()                
    except mysql.connector.Error as e:
        print(e)

if __name__ == "__main__":    
    parser = argparse.ArgumentParser()
    parser.add_argument("--assessment-name", "-an", help="assessment name", type=str)
    parser.add_argument("--project-id", "-p", help="project id", type=int)
    parser.add_argument("--multiple-choice-weight", "-mcw", help="weight of the multiple choice questions", type=float)
    parser.add_argument("--code-weight", "-cw", help="weight of the code challenges", type=float)
    parser.add_argument("--status", "-s", help="status of challenge (submitted || all)", type=str)
    args = parser.parse_args()

    if not args.assessment_name or not args.project_id:
        print("Você precisa informar o nome do desafio e o ID do projeto")
        sys.exit()

    if not args.multiple_choice_weight or not args.code_weight:
        print("Você precisa informar o peso das questões de múltipla escolha e o peso dos desafios de programação")
        sys.exit()
    
    if (args.multiple_choice_weight + args.code_weight) != 100:
        print("Peso das questões informado deve totalizar 100%")
        sys.exit()

    driver = webdriver.Chrome()
    assessment_links = get_links_from_assessment(driver, CODERBYTE_URL, args.assessment_name)
    scores_list = list(map(lambda x: get_scores_from_assesment(driver, x, args.multiple_choice_weight, args.code_weight, args.status), assessment_links))
    # assessment_links = get_links_from_assessment(driver, CODERBYTE_URL, "T-Academy")
    # scores_list = list(map(lambda x: get_scores_from_assesment(driver, x, 30, 70, None), assessment_links))
    driver.close()

    # Achatando a lista de resultados
    scores = list(itertools.chain(*scores_list))

    formatted_scores_list = remove_duplicates(scores)

    save_challenges_in_db(formatted_scores_list, args.project_id)
    print("Desafios cadastrados :D")