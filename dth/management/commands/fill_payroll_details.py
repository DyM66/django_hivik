# dth/management/commands/fill_payroll_details.py

from django.core.management.base import BaseCommand
from django.db import transaction
from openpyxl import load_workbook

from dth.models import Nomina, PayrollDetails, EPS

import re
import datetime

class Command(BaseCommand):
    """
    Lee un archivo Excel (con hoja 'MARZO') a partir de la fila 4 y
    actualiza la información de Nomina/PayrollDetails en base a
    distintas columnas.
    """
    help = "Lee un Excel y actualiza campos en Nomina y PayrollDetails"

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help="Ruta local del archivo Excel a procesar")

    @transaction.atomic
    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            wb = load_workbook(filename=excel_path, data_only=True)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"El archivo '{excel_path}' no fue encontrado."))
            return
        
        # Asegurarnos de que existe la hoja 'MARZO'
        sheet_name = 'MARZO'
        if sheet_name not in wb.sheetnames:
            self.stdout.write(self.style.ERROR(f"No se encontró la hoja '{sheet_name}' en el Excel."))
            return
        
        ws = wb[sheet_name]

        self.stdout.write(self.style.NOTICE(f"Abriendo hoja '{sheet_name}'..."))

        # Diccionarios de mapeo
        gender_map = {
            'M': 'h',  # Masculino => 'h'
            'F': 'm',  # Femenino => 'm'
        }
        education_map = {
            'Ninguno': 'none',
            'Primaria Incompleta': 'sec_incompleta',
            'Primaria Completa': 'sec_incompleta',
            'Secundaria Incompleta': 'sec_incompleta',
            'Secundaria Completa': 'sec_completa',
            'Técnico': 'tecnico',
            'Tecnólogo': 'tecnologo',
            'Pregrado': 'pregrado',
            'Postgrado': 'postgrado',
        }
        marital_map = {
            'casado': ['Casado/da', 'casado/da', 'casado/a', 'casado(da)'],
            'unionlibre': ['Union Libre', 'Unión Libre'],
            'soltero': ['Soltero/ra', 'soltero/ra', 'soltero(a)'],
            'viudo': ['Viudo(a)', 'viudo(a)'],
            'divorciado': ['Divorciado(a)', 'divorciado(a)'],
        }
        shift_map = {
            '5 x 2 (Lunes a Viernes)': '5x2',
            '6 x 1': '6x1',
            '6 x 1 (Navegando 2 x 1)': '6x1_nav',
            '14 x 7': '14x7',
            'Jornada Flexible': 'flexible',
            '14 x 14 (1 x 1)': '14x14',
        }
        criticity_map = {
            'BAJO': 'bajo',
            'MEDIO': 'medio',
            'ALTO': 'alto',
        }
        salary_type_map = {
            'Ordinario': 'ordinario',
            'Variable': 'variable',
            'Integral': 'integral',
            'Especie': 'especie',
        }

        # Cache para EPS (para no buscar repetidas veces)
        eps_cache = {}
        
        # Contadores para el resumen
        total_rows_processed = 0
        updated_nomina_count = 0
        updated_details_count = 0
        no_nomina_count = 0

        # Empezamos a leer a partir de la fila 4
        row_index = 4
        while True:
            # ------------------------------
            # 1) Col C => Identificacion
            # ------------------------------
            id_number_cell = f"C{row_index}"
            id_number_val = ws[id_number_cell].value

            # Si no hay valor => fin de datos
            if not id_number_val:
                self.stdout.write(self.style.WARNING(
                    f"Fin de datos al llegar a fila {row_index}. No se encontró 'id_number'."
                ))
                break

            # Convierto a str (por si es int/float)
            id_number_str = str(id_number_val).strip()
            
            # Salto si es "Identificacion" (cabecera)
            if id_number_str.lower() == "identificacion":
                self.stdout.write(self.style.WARNING(
                    f"No se encontró registro en Nomina con id_number={id_number_str} (fila {row_index})."
                ))
                user_decision = input("¿Deseas continuar con la siguiente fila? (s/n): ").lower()
                if user_decision.startswith('n'):
                    break
                row_index += 1
                continue

            # Buscamos en DB
            try:
                nomina_obj = Nomina.objects.get(id_number=id_number_str)
            except Nomina.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"No se encontró registro en Nomina con id_number={id_number_str} (fila {row_index})."
                ))
                no_nomina_count += 1
                user_decision = input("¿Deseas continuar con la siguiente fila? (s/n): ").lower()
                if user_decision.startswith('n'):
                    break
                row_index += 1
                continue

            details_obj, _created = PayrollDetails.objects.get_or_create(nomina=nomina_obj)

            row_updates_nomina = False
            row_updates_details = False

            # ------------------------------------------------------
            # 2) Col G => género => "M" / "F"
            # ------------------------------------------------------
            g_cell = f"G{row_index}"
            excel_gender_val = ws[g_cell].value
            excel_gender_str = safe_str_cell(excel_gender_val).upper()  # "M" / "F"
            if excel_gender_str in gender_map:
                desired_gender = gender_map[excel_gender_str]
                if nomina_obj.gender != desired_gender:
                    nomina_obj.gender = desired_gender
                    row_updates_nomina = True

            # ------------------------------------------------------
            # 3) Col K => birth_date => "DD-MM-YYYY" (posible)
            # ------------------------------------------------------
            k_cell = f"K{row_index}"
            excel_birth_val = ws[k_cell].value
            birth_date = parse_excel_date(excel_birth_val)
            if birth_date is not None and details_obj.birth_date != birth_date:
                details_obj.birth_date = birth_date
                row_updates_details = True

            # ------------------------------------------------------
            # 4) Col M => place_of_birth
            # ------------------------------------------------------
            m_cell = f"M{row_index}"
            place_of_birth_val = safe_str_cell(ws[m_cell].value)
            if place_of_birth_val and details_obj.place_of_birth != place_of_birth_val:
                details_obj.place_of_birth = place_of_birth_val
                row_updates_details = True

            # ------------------------------------------------------
            # 5) Col N => doc_expedition_date
            # ------------------------------------------------------
            n_cell = f"N{row_index}"
            doc_expedition_val = ws[n_cell].value
            doc_expedition_date = parse_excel_date(doc_expedition_val)
            if doc_expedition_date and details_obj.doc_expedition_date != doc_expedition_date:
                details_obj.doc_expedition_date = doc_expedition_date
                row_updates_details = True

            # ------------------------------------------------------
            # 6) Col O => doc_expedition_department
            # ------------------------------------------------------
            o_cell = f"O{row_index}"
            depto_val = safe_str_cell(ws[o_cell].value)
            if depto_val and details_obj.doc_expedition_department != depto_val:
                details_obj.doc_expedition_department = depto_val
                row_updates_details = True

            # ------------------------------------------------------
            # 7) Col P => doc_expedition_municipality
            # ------------------------------------------------------
            p_cell = f"P{row_index}"
            mun_val = safe_str_cell(ws[p_cell].value)
            if mun_val and details_obj.doc_expedition_municipality != mun_val:
                details_obj.doc_expedition_municipality = mun_val
                row_updates_details = True

            # ------------------------------------------------------
            # 8) Col Q => education_level
            # ------------------------------------------------------
            q_cell = f"Q{row_index}"
            edu_val = safe_str_cell(ws[q_cell].value)
            if edu_val in education_map:
                final_edu = education_map[edu_val]
                if details_obj.education_level != final_edu:
                    details_obj.education_level = final_edu
                    row_updates_details = True

            # ------------------------------------------------------
            # 9) Col R => profession
            # ------------------------------------------------------
            r_cell = f"R{row_index}"
            prof_val = safe_str_cell(ws[r_cell].value)
            if prof_val and details_obj.profession != prof_val:
                details_obj.profession = prof_val
                row_updates_details = True

            # ------------------------------------------------------
            # 10) Col V => last_academic_institution
            # ------------------------------------------------------
            v_cell = f"V{row_index}"
            last_inst_val = safe_str_cell(ws[v_cell].value)
            if last_inst_val and details_obj.last_academic_institution != last_inst_val:
                details_obj.last_academic_institution = last_inst_val
                row_updates_details = True

            # ------------------------------------------------------
            # 11) Col W => phone => EN NOMINA
            # ------------------------------------------------------
            w_cell = f"W{row_index}"
            phone_val = safe_str_cell(ws[w_cell].value)
            if phone_val and nomina_obj.phone != phone_val:
                nomina_obj.phone = phone_val
                row_updates_nomina = True

            # ------------------------------------------------------
            # 12) Col X => municipality_of_residence => PAYROLLDETAILS
            # ------------------------------------------------------
            x_cell = f"X{row_index}"
            mun_res_val = safe_str_cell(ws[x_cell].value)
            if mun_res_val and details_obj.municipality_of_residence != mun_res_val:
                details_obj.municipality_of_residence = mun_res_val
                row_updates_details = True

            # ------------------------------------------------------
            # 13) Col Y => address => PAYROLLDETAILS
            # ------------------------------------------------------
            y_cell = f"Y{row_index}"
            addr_val = safe_str_cell(ws[y_cell].value)
            if addr_val and details_obj.address != addr_val:
                details_obj.address = addr_val
                row_updates_details = True

            # ------------------------------------------------------
            # 14) Col Z => email => NOMINA
            # ------------------------------------------------------
            z_cell = f"Z{row_index}"
            email_val = safe_str_cell(ws[z_cell].value)
            if email_val and nomina_obj.email != email_val:
                nomina_obj.email = email_val
                row_updates_nomina = True

            # ------------------------------------------------------
            # 15) Col AA => rh => PAYROLLDETAILS
            # ------------------------------------------------------
            aa_cell = f"AA{row_index}"
            rh_val = safe_str_cell(ws[aa_cell].value)
            if rh_val and details_obj.rh != rh_val:
                details_obj.rh = rh_val
                row_updates_details = True

            # ------------------------------------------------------
            # 16) Col AB => marital_status => PAYROLLDETAILS
            # ------------------------------------------------------
            ab_cell = f"AB{row_index}"
            ms_val = safe_str_cell(ws[ab_cell].value)
            final_ms = map_any(ms_val, marital_map)
            if final_ms and details_obj.marital_status != final_ms:
                details_obj.marital_status = final_ms
                row_updates_details = True

            # ------------------------------------------------------
            # 17) Col AD => EPS => PAYROLLDETAILS (FK)
            # ------------------------------------------------------
            ad_cell = f"AD{row_index}"
            eps_name_val = safe_str_cell(ws[ad_cell].value)
            if eps_name_val:
                # Chequeamos cache
                if eps_name_val in eps_cache:
                    eps_obj = eps_cache[eps_name_val]
                else:
                    try:
                        eps_obj = EPS.objects.get(name__iexact=eps_name_val)
                        eps_cache[eps_name_val] = eps_obj
                    except EPS.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"No se encontró EPS '{eps_name_val}' en la BD."
                        ))
                        user_inp = input("Ingresa manualmente el ID de EPS o deja vacío para omitir: ").strip()
                        if user_inp:
                            try:
                                eps_obj = EPS.objects.get(pk=user_inp)
                                eps_cache[eps_name_val] = eps_obj
                            except EPS.DoesNotExist:
                                self.stdout.write(self.style.ERROR("ID de EPS inválido. Omitiendo..."))
                                eps_obj = None
                        else:
                            eps_obj = None
                if eps_obj and details_obj.eps != eps_obj:
                    details_obj.eps = eps_obj
                    row_updates_details = True

            # ------------------------------------------------------
            # 18) Col AE => AFP => PAYROLLDETAILS
            # ------------------------------------------------------
            ae_cell = f"AE{row_index}"
            afp_val = safe_str_cell(ws[ae_cell].value).lower()
            if afp_val:
                if afp_val.startswith('prot'):
                    afp_val = 'proteccion'
                elif afp_val.startswith('porv'):
                    afp_val = 'porvenir'
                elif afp_val.startswith('colp'):
                    afp_val = 'colpensiones'
                if details_obj.afp != afp_val:
                    details_obj.afp = afp_val
                    row_updates_details = True

            # ------------------------------------------------------
            # 19) Col AG => caja_compensacion => PAYROLLDETAILS
            # ------------------------------------------------------
            ag_cell = f"AG{row_index}"
            ccomp_val = safe_str_cell(ws[ag_cell].value)
            if ccomp_val and details_obj.caja_compensacion != ccomp_val:
                details_obj.caja_compensacion = ccomp_val
                row_updates_details = True

            # ------------------------------------------------------
            # 20) Col AM => center_of_work => PAYROLLDETAILS
            # ------------------------------------------------------
            am_cell = f"AM{row_index}"
            cow_val = safe_str_cell(ws[am_cell].value).lower()
            if 'cartagena' in cow_val:
                cow_val = 'cartagena'
            elif 'guyana' in cow_val:
                cow_val = 'guyana'
            if cow_val and details_obj.center_of_work != cow_val:
                details_obj.center_of_work = cow_val
                row_updates_details = True

            # ------------------------------------------------------
            # 21) Col AO => contract_type => PAYROLLDETAILS
            # ------------------------------------------------------
            ao_cell = f"AO{row_index}"
            ctype_val = safe_str_cell(ws[ao_cell].value).lower()
            if ctype_val.startswith('inde'):
                ctype_val = 'indefinido'
            elif ctype_val.startswith('defin'):
                ctype_val = 'definido'
            elif ctype_val.startswith('aprend'):
                ctype_val = 'aprendizaje'
            elif ctype_val.startswith('obra'):
                ctype_val = 'obra'
            if ctype_val and details_obj.contract_type != ctype_val:
                details_obj.contract_type = ctype_val
                row_updates_details = True

            # ------------------------------------------------------
            # 22) Col AR => months_term => payrollDETAILS
            # ------------------------------------------------------
            ar_cell = f"AR{row_index}"
            mt_val = ws[ar_cell].value
            if isinstance(mt_val, int) and mt_val > 0:
                if details_obj.months_term != mt_val:
                    details_obj.months_term = mt_val
                    row_updates_details = True

            # ------------------------------------------------------
            # 23) Col AZ => shift => payrollDETAILS
            # ------------------------------------------------------
            az_cell = f"AZ{row_index}"
            shift_raw_val = safe_str_cell(ws[az_cell].value)
            final_shift = shift_map.get(shift_raw_val, None)
            if final_shift and details_obj.shift != final_shift:
                details_obj.shift = final_shift
                row_updates_details = True

            # ------------------------------------------------------
            # 24) Col BB => criticity_level => payrollDETAILS
            # ------------------------------------------------------
            bb_cell = f"BB{row_index}"
            crit_raw_val = safe_str_cell(ws[bb_cell].value).upper()
            final_crit = criticity_map.get(crit_raw_val, None)
            if final_crit and details_obj.criticity_level != final_crit:
                details_obj.criticity_level = final_crit
                row_updates_details = True

            # ------------------------------------------------------
            # 25) Col BC => salary_type => payrollDETAILS
            # ------------------------------------------------------
            bc_cell = f"BC{row_index}"
            stype_raw_val = safe_str_cell(ws[bc_cell].value)
            final_stype = salary_type_map.get(stype_raw_val, None)
            if final_stype and details_obj.salary_type != final_stype:
                details_obj.salary_type = final_stype
                row_updates_details = True

            # ------------------------------------------------------
            # 26) Col BE => bank_account => payrollDETAILS
            # ------------------------------------------------------
            be_cell = f"BE{row_index}"
            bacc_val = safe_str_cell(ws[be_cell].value)
            if bacc_val and details_obj.bank_account != bacc_val:
                details_obj.bank_account = bacc_val
                row_updates_details = True

            # ------------------------------------------------------
            # 27) Col BF => bank => payrollDETAILS
            # ------------------------------------------------------
            bf_cell = f"BF{row_index}"
            bank_val = safe_str_cell(ws[bf_cell].value)
            if bank_val and details_obj.bank != bank_val:
                details_obj.bank = bank_val
                row_updates_details = True

            # Guardamos si hubo cambios
            if row_updates_nomina:
                nomina_obj.save()
                updated_nomina_count += 1
            if row_updates_details:
                details_obj.save()
                updated_details_count += 1

            total_rows_processed += 1
            self.stdout.write(f"Fila {row_index} => id_number={id_number_str} procesada.")

            # Pasamos a la siguiente fila
            row_index += 1

        # --- Fin while True ---
        self.stdout.write(self.style.SUCCESS("=== RESUMEN DE PROCESAMIENTO ==="))
        self.stdout.write(f"Filas procesadas: {total_rows_processed}")
        self.stdout.write(f"Nominas sin coincidencia: {no_nomina_count}")
        self.stdout.write(f"Nominas actualizadas: {updated_nomina_count}")
        self.stdout.write(f"Details actualizados: {updated_details_count}")
        self.stdout.write(self.style.SUCCESS("Proceso finalizado."))


def parse_excel_date(value):
    """
    Intenta parsear un valor (string, datetime de Excel, etc.) y devolver un date.
    - Si es datetime.date/datetime.datetime => lo convertimos.
    - Si es string 'DD-MM-YYYY' => parse manual.
    - Devuelve None si no pudo.
    """
    if not value:
        return None
    
    if isinstance(value, datetime.date):
        return value  # ya es date/datetime

    text = str(value).strip()
    # Regex dd-mm-yyyy
    match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})$', text)
    if match:
        day, month, year = match.groups()
        day, month, year = int(day), int(month), int(year)
        try:
            return datetime.date(year, month, day)
        except ValueError:
            return None

    # Regex yyyy-mm-dd
    match2 = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', text)
    if match2:
        year, month, day = match2.groups()
        year, month, day = int(year), int(month), int(day)
        try:
            return datetime.date(year, month, day)
        except ValueError:
            return None

    return None

def safe_str_cell(value):
    """
    Convierte un valor (None, int, float, str) a str y hace strip().
    Retorna '' si value es None.
    """
    if value is None:
        return ''
    return str(value).strip()

def map_any(value_str, mapping_dict):
    """
    Toma un string (value_str) y un diccionario:
      e.g. {
        'casado': ['Casado/da','casado/da','casado(a)'],
        'unionlibre': ['Union Libre','Unión Libre'],
      }
    y si value_str coincide con alguno de los sinónimos (ignorando may/min),
    retorna la key. Si no coincide, retorna None.
    """
    val_lower = value_str.lower()
    for final_key, synonyms in mapping_dict.items():
        for syn in synonyms:
            if syn.lower() == val_lower:
                return final_key
    return None
