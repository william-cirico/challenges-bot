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
PASSWORD = "Pr0w4!@2022"

def formatScore(score: str) -> float:
    """Formats the score in '%d' format to float"""
    return float(score.replace("%", ""))

def getScoresFromAssesment(driver: any, assesmentURL: str) -> List[Tuple[float, str]]:
    """Returns the scores from an acessment"""
    driver.get(assesmentURL)

    # Obtendo os testes
    scores_elements = driver.find_elements(By.XPATH, "//span[contains(., 'Submitted')]/following-sibling::span[contains(@class, 'score')]")
    emails_elements = driver.find_elements(By.XPATH, "//span[contains(., 'Submitted')]/preceding-sibling::span[1]")
    
    # Convertendo os scores
    formatted_scores = list(map(lambda score: formatScore(score.text), scores_elements))

    # Obtendo os emails
    emails = list(map(lambda email: email.text, emails_elements))

    # Juntando score e email em tuplas
    return list(zip(formatted_scores, emails))


def getSubmittedAssesmentsFromUrl(assesment_url: str, assessment_name: str) -> any:
    """Get all the sumitted assesments from an URL"""
    driver = webdriver.Chrome()
    driver.get(assesment_url)

    # Realizando o login
    [email_input, pass_input] = driver.find_elements(By.CLASS_NAME, "login-field-input")
    email_input.send_keys(USERNAME)
    pass_input.send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[text()='login']").click()    

    # Navegando para a página de avaliações
    wait = WebDriverWait(driver, 10)
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Assessments"))).click()
    
    # Localizando os links dos desafios
    assesments_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, f"//h3[contains(., '{assessment_name}')]/following-sibling::a[1]")))
    
    # Obtendo os links
    links = list(map(lambda x: x.get_attribute("href"), assesments_links))
        
    # Obtendo a lista de scores
    scores_lists = list(map(lambda x: getScoresFromAssesment(driver, x), links))

    driver.close()

    # Achatando a lista de resultados
    scores =list(itertools.chain(*scores_lists))

    return scores


def saveChallengesInDB(assessment_scores: List[Tuple[float, str]], project_id: int):
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

                for assessment_score in assesments_scores:                    
                    cursor.execute(sql, assessment_score)
                
                connection.commit()
    except mysql.connector.Error as e:
        print(e)

if __name__ == "__main__":    
    parser = argparse.ArgumentParser()
    parser.add_argument("--assessment-name", "-an", help="assessment name", type=str)
    parser.add_argument("--project-id", "-p", help="project id", type=int)
    args = parser.parse_args()

    if not args.assessment_name or not args.project_id:
        print("Você precisa informar o nome do desafio e o ID do projeto")
        sys.exit()

    assesments_scores = getSubmittedAssesmentsFromUrl(CODERBYTE_URL, args.assessment_name)
    saveChallengesInDB(assesments_scores, args.project_id)
    print("Desafios cadastrados 😄")
