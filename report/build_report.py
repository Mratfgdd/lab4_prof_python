import argparse
import ast
import html
import inspect
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
PDF_PATH = ROOT / "Звіт_ЛР4_Левандівський.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(REPORT_DIR))

from class_diagram import render as render_diagram

from domain_app import (
    dto,
    main,
    models,
    policies,
    protocols,
    registry,
    repositories,
    services,
    value_objects,
)

ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
PROMPT = r"PS C:\Github\prof_python\Lab_04>"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def code(source: str, keep: bool | None = None) -> str:
    text = source.strip("\n")
    if keep is None:
        keep = text.count("\n") < 16
    return f'<pre class="code{" keep" if keep else ""}">{esc(text)}</pre>'


def strip_docstrings(source: str) -> str:
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    drop: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str) and first.end_lineno is not None:
                    drop.update(range(first.lineno, first.end_lineno + 1))
    kept = [line for n, line in enumerate(source.splitlines(), 1) if n not in drop]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip("\n")


def src(*objects: object, keep: bool | None = None) -> str:
    parts = []
    for obj in objects:
        target = obj.fget if isinstance(obj, property) else obj
        parts.append(strip_docstrings(inspect.getsource(target)))
    return code("\n\n".join(parts), keep)


def class_excerpt(cls: type, *methods: str) -> str:
    head: list[str] = []
    for line in inspect.getsource(cls).splitlines():
        if line.startswith("    ") and line.strip().startswith(("def ", "@")):
            break
        head.append(line)
    parts = [strip_docstrings("\n".join(head))]
    for name in methods:
        member = cls.__dict__[name]
        if isinstance(member, classmethod | staticmethod):
            member = member.__func__
        elif isinstance(member, property):
            member = member.fget
        parts.append(textwrap.indent(strip_docstrings(inspect.getsource(member)), "    "))
    return "\n\n".join(parts) + "\n\n    ..."


def module_lines(module: object, pattern: str) -> str:
    lines = inspect.getsource(module).splitlines()
    return "\n".join(line for line in lines if re.match(pattern, line))


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8", check=False
    )


def terminal(command: str, output: str) -> str:
    return (
        f'<div class="term"><span class="ps">{esc(PROMPT)}</span> {esc(command)}\n'
        f"{esc(output.rstrip())}</div>"
    )


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def keep_numbers_together(markup: str) -> str:
    pieces = re.split(
        r"(<pre.*?</pre>|<div class=\"term\">.*?</div>|<svg.*?</svg>)", markup, flags=re.S
    )
    return "".join(
        piece
        if piece.startswith(("<pre", '<div class="term"', "<svg"))
        else re.sub(r"(?<=\d) (?=\d{3}\b)", "\u00a0", piece)
        for piece in pieces
    )


class Numbering:
    def __init__(self) -> None:
        self.table = 0
        self.figure = 0

    def tcap(self, text: str) -> str:
        self.table += 1
        return f'<p class="tcap">Таблиця {self.table} – {text}</p>'

    def fcap(self, text: str) -> str:
        self.figure += 1
        return f'<p class="fcap">Рисунок {self.figure} – {text}</p>'


def program_output() -> str:
    result = run([sys.executable, "-m", "domain_app.main"])
    assert result.returncode == 0, result.stderr
    return result.stdout


def di_output() -> str:
    result = run([sys.executable, "experiments/di_comparison.py"])
    assert result.returncode == 0, result.stderr
    return result.stdout


def mypy(venv: Path, *paths: str, expect_ok: bool) -> str:
    result = run(
        [str(venv / "Scripts" / "mypy.exe"), "--no-incremental", "--cache-dir=nul", *paths]
    )
    assert (result.returncode == 0) == expect_ok, result.stdout + result.stderr
    return result.stdout.strip()


def ci_check(venv: Path) -> str:
    result = subprocess.run(
        [str(venv / "Scripts" / "python.exe"), "tools/check.py"],
        cwd=ROOT,
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert re.search(r"Ran \d+ tests? in [\d.]+s\s+OK", result.stdout), result.stdout
    return result.stdout.strip()


CSS = """
@page { size: A4; margin: 20mm 15mm 20mm 30mm;
  @bottom-center { content: counter(page); font: 12pt "Times New Roman", serif; } }
@page :first { @bottom-center { content: none; } }
html { background: #fff; }
body { margin: 0; color: #000; background: #fff; font-family: "Times New Roman", serif;
  font-size: 14pt; line-height: 1.22; }
p { margin: 0 0 2pt; text-indent: 1.25cm; text-align: justify; }
h1 { font-size: 14pt; text-align: center; margin: 9pt 0 4pt; break-after: avoid; }
h2 { font-size: 14pt; margin: 6pt 0 3pt; text-indent: 1.25cm; break-after: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 0.82em; }
pre.code { font-family: Consolas, "Courier New", monospace; font-size: 8.2pt;
  line-height: 1.13; margin: 3pt 0 5pt; padding: 3pt 8pt; white-space: pre-wrap;
  background: #f6f6f4; border-left: 3px solid #c3c2b7; orphans: 4; widows: 4; }
pre.keep { break-inside: avoid; }
.term { font-family: Consolas, "Courier New", monospace; font-size: 7.4pt; line-height: 1.14;
  white-space: pre-wrap; background: #0c0c0c; color: #d4d4d4; padding: 4pt 8pt;
  border-radius: 4px; margin: 3pt 0 3pt; orphans: 4; widows: 4; }
.term .ps { color: #f9f1a5; }
table { width: 100%; border-collapse: collapse; font-size: 10.5pt; line-height: 1.13;
  margin: 2pt 0 5pt; }
th, td { border: 1px solid #000; padding: 1.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #f0efec; }
tr { break-inside: avoid; }
.tcap { text-indent: 0; text-align: left; margin: 4pt 0 2pt; break-after: avoid; }
.fcap { text-indent: 0; text-align: center; margin: 3pt 0 5pt; }
.figure { break-inside: avoid; margin: 2pt 0 0; }
.figure svg { width: 100%; height: auto; }
@page land { size: A4 landscape; margin: 12mm 15mm 14mm 20mm;
  @bottom-center { content: counter(page); font: 12pt "Times New Roman", serif; } }
.landscape { page: land; break-before: page; break-after: page; }
.landscape h1 { margin-top: 0; }
.landscape .figure svg { width: auto; height: 152mm; display: block; margin: 0 auto; }
.title { height: 255mm; display: flex; flex-direction: column; justify-content: space-between;
  text-align: center; break-after: page; line-height: 1.5; }
.title .main { margin-top: 30mm; }
.title .main .big { font-size: 20pt; font-weight: bold; letter-spacing: 2pt; }
.title .main .theme { font-size: 16pt; font-weight: bold; margin-top: 10pt; }
.title .sign { align-self: flex-end; text-align: left; width: 85mm; margin-top: 30mm; }
.title .city { margin-top: auto; }
"""


def build_html(venv: Path) -> str:
    n = Numbering()
    output = program_output()
    errors = mypy(venv, "experiments/type_errors.py", expect_ok=False)
    fixed = mypy(
        venv, "experiments/type_errors_fixed.py", "experiments/di_comparison.py", expect_ok=True
    )
    strict = mypy(venv, expect_ok=True)
    checks = ci_check(venv)
    di = di_output()
    total_tests = int(re.search(r"Ran (\d+) tests?", checks).group(1))
    error_lines = [ln for ln in errors.splitlines() if ": error:" in ln]
    assert len(error_lines) == 7, errors

    reg = main.build_registry()
    main.load_demo_data(reg)
    anna = reg.get(1)
    simple, weighted = policies.SimpleAverage(), policies.CreditWeightedAverage()
    best_two = policies.BestResultsAverage(2)
    averages = [str(anna.average(p)) for p in (simple, weighted, best_two)]
    assert averages == ["91.50", "92.04", "92.50"], averages
    for expected in ("91.50", "92.04", "92.50", "88.07", "77.98", "76.47", "63.90"):
        assert expected in output, expected
    manual = (Decimal("90") * 5 + Decimal("95") * 6 + Decimal("89.5") * 3) / 14
    assert round(manual, 2) == Decimal("92.04")

    parts: list[str] = []
    add = parts.append

    add("""
<section class="title">
  <div>МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ<br>
  Львівський національний університет імені Івана Франка</div>
  <div class="main">
    <div class="big">ЗВІТ</div>
    <div>до лабораторної роботи №4</div>
    <div>з дисципліни «Професійний Python»</div>
    <div class="theme">Тема: «Професійне ООП та система типів Python»</div>
  </div>
  <div class="sign">Виконав:<br>студент Левандівський Назар<br><br>
  Перевірив:<br>Куньо Іван Михайлович</div>
  <div class="city">Львів – 2026</div>
</section>""")

    add("<h1>Мета роботи</h1>")
    add(
        "<p>Сформувати навички побудови типізованої об'єктно-орієнтованої моделі предметної "
        "області: класи, композиція і наслідування, ABC та Protocol, dataclass і value "
        "objects, properties, dunder methods, принципи SOLID, dependency injection, generic "
        "classes, TypeVar, TypedDict і статична перевірка коду через mypy.</p>"
    )

    add("<h1>1. Предметна область і постановка задачі</h1>")
    add(
        "<p><b>Варіант 1. Система обліку студентів</b> (продовження ЛР1–ЛР3). Студент "
        "навчається в групі й має академічний запис – набір результатів із предметів; кожен "
        "результат складається з оцінки (0–100) і кількості кредитів. Студенти бувають "
        "бюджетні й контрактні, а стипендію отримують лише бюджетні з достатнім середнім "
        "балом. Оцінки зберігаються як <code>Decimal</code>, бо float дає похибки округлення. "
        "Спосіб обчислення середнього бала змінюється стратегією: простий, зважений за "
        "кредитами або середнє з кількох найкращих оцінок.</p>"
    )
    add(n.tcap("Вимоги варіанта та їх реалізація"))
    add(
        table(
            ["Вимога", "Реалізація"],
            [
                [
                    "додавання та редагування даних студента",
                    "<code>StudentService.register</code>, <code>edit</code>; <code>Student.edit</code> "
                    "перевіряє нові значення до зміни стану",
                ],
                [
                    "пошук за прізвищем/ID і групою",
                    "<code>find_by_last_name</code> (без урахування регістру), <code>find_by_id</code>, "
                    "<code>find_in_group</code>",
                ],
                [
                    "обчислення середнього бала",
                    "<code>AcademicRecord.average(policy)</code> і стратегії <code>GradingPolicy</code>",
                ],
                [
                    "визначення найкращого студента",
                    "<code>StudentRegistry.best_student(policy, group)</code>, <code>Group.best</code>",
                ],
                [
                    "repository",
                    "<code>Repository[K, T]</code> (ABC) і <code>InMemoryRepository[K, T]</code>",
                ],
                [
                    "reporting service",
                    "<code>ReportService</code>: summaries, ranking, group_report, card",
                ],
                [
                    "notification abstraction",
                    "<code>Notifier</code> (runtime_checkable Protocol) і адаптери "
                    "<code>ConsoleNotifier</code>, <code>MemoryNotifier</code>",
                ],
            ],
        )
    )
    add(n.tcap("Domain objects та інші класи моделі"))
    add(
        table(
            ["Клас", "Вид", "Відповідальність"],
            [
                [
                    "<code>Student</code>, <code>BudgetStudent</code>, <code>ContractStudent</code>",
                    "dataclass, entity; підкласи",
                    "дані студента, ідентичність за id, стипендія",
                ],
                ["<code>Group</code>", "entity, колекція", "склад групи, середній бал, найкращий"],
                [
                    "<code>AcademicRecord</code>",
                    "custom collection",
                    "результати студента (один на предмет)",
                ],
                [
                    "<code>Grade</code>, <code>GroupCode</code>, <code>CourseResult</code>",
                    "frozen value objects",
                    "оцінка 0–100; код групи PI-21; оцінка з предмета й кредитами",
                ],
                [
                    "<code>StudentRegistry</code>",
                    "aggregate root",
                    "інваріанти: студент завжди в існуючій групі",
                ],
                [
                    "<code>GradingPolicy</code> і 3 підкласи",
                    "ABC, strategy",
                    "обчислення середнього бала",
                ],
                [
                    "<code>StudentService</code>, <code>ReportService</code>",
                    "application services",
                    "сценарії та сповіщення; звітність",
                ],
                ["<code>StudentError</code> і 6 підкласів", "ієрархія винятків", "доменні помилки"],
            ],
        )
    )

    caption = n.fcap(
        "UML class diagram моделі (◇ агрегація, ◆ композиція, △ наслідування, пунктир із △ – "
        "реалізація Protocol, пунктирна стрілка – використання або «inject»)"
    )
    add(
        f'<section class="landscape"><h1>2. Діаграма класів</h1>'
        f'<div class="figure">{render_diagram()}{caption}</div></section>'
    )

    add("<h1>3. Inheritance, composition, encapsulation</h1>")
    add(
        "<p><b>Inheritance</b> застосовано там, де є справжнє is-a. <code>GradingPolicy</code> "
        "– ABC з абстрактним <code>average</code>; кожен підклас оголошується з іменем "
        '(<code>class SimpleAverage(GradingPolicy, name="simple")</code>) і реєструється '
        "через <code>__init_subclass__</code>, тому фабрика <code>GradingPolicy.create(name)</code> "
        "знає всі стратегії без жодного списку. <code>BudgetStudent</code> і "
        "<code>ContractStudent</code> є студентами: базовий <code>has_scholarship</code> "
        "повертає False, а бюджетний підклас перевизначає його.</p>"
    )
    add(
        code(
            class_excerpt(policies.GradingPolicy, "__init_subclass__", "create", "average")
            + "\n\n"
            + strip_docstrings(inspect.getsource(policies.CreditWeightedAverage))
            + "\n\n# class BudgetStudent(Student)\n"
            + strip_docstrings(inspect.getsource(models.BudgetStudent.has_scholarship)),
            keep=False,
        )
    )
    add(
        "<p><b>Composition</b> (has-a): студент має <code>AcademicRecord</code> і "
        "<code>GroupCode</code>, запис має <code>CourseResult</code>, група має студентів, "
        "реєстр має два репозиторії, сервіс – реєстр, notifier і політику. <b>Encapsulation</b>: "
        "<code>full_name</code> – property без setter, <code>Group.members</code> і "
        "<code>AcademicRecord.results</code> повертають копію-кортеж, а студент потрапляє в "
        "групу лише через <code>Group.add</code>, який узгоджує поле <code>student.group</code>.</p>"
    )
    add(src(models.Student.full_name, models.Group.members, models.Group.add))

    add("<h1>4. Dataclass і immutable value object</h1>")
    add(
        "<p><code>Grade</code> – frozen dataclass зі <code>slots=True</code>: незмінний, hashable, "
        "порівнюється за значенням. У <code>__post_init__</code> перевіряється діапазон 0–100 і "
        "значення нормалізується до сотих; <code>total_ordering</code> добудовує "
        "<code>&lt;= &gt; &gt;=</code> з <code>__lt__</code>, <code>of()</code> свідомо не "
        "приймає float, а <code>level</code> – property з рівнем успішності. "
        "<code>Student</code> – змінюваний dataclass з <code>eq=False</code>: рівність і хеш "
        "визначає лише <code>id</code> (entity), а поля перевіряються в "
        "<code>__post_init__</code>.</p>"
    )
    add(
        code(
            class_excerpt(value_objects.Grade, "__post_init__", "of", "level", "__lt__"), keep=False
        )
    )
    add(code(class_excerpt(models.Student, "__post_init__", "edit", "__eq__"), keep=False))

    add("<h1>5. ABC, Protocol, generics і TypedDict</h1>")
    add(
        "<p><code>Repository</code> – ABC (nominal typing) і водночас generic class. "
        "<code>K</code> – constrained TypeVar (ключ лише <code>int</code> або "
        "<code>GroupCode</code>), <code>T</code> – звичайний TypeVar, <code>S</code> у реєстрі "
        "й сервісі – bound TypeVar: <code>register(BudgetStudent(...))</code> повертає саме "
        "<code>BudgetStudent</code>.</p>"
    )
    add(
        code(
            module_lines(repositories, r"^(K|T) = ")
            + "\n"
            + module_lines(registry, r"^S = ")
            + "\n\n"
            + strip_docstrings(inspect.getsource(repositories.Repository))
        )
    )
    add(
        "<p><code>Notifier</code> – Protocol (structural typing): адаптери його не успадковують, "
        "але сумісні за сигнатурою <code>send</code>; завдяки <code>@runtime_checkable</code> "
        "працює <code>isinstance</code>. Три вузькі протоколи <code>Parser</code>, "
        "<code>Validator</code>, <code>Formatter</code> – interface segregation. TypedDict "
        "описує зовнішній JSON-payload студента; під час виконання це звичайний dict, тому його "
        "перетворює на доменний об'єкт <code>student_from_payload</code>.</p>"
    )
    add(
        code(
            strip_docstrings(inspect.getsource(protocols.Notifier))
            + "\n\n"
            + strip_docstrings(inspect.getsource(dto.StudentPayload))
        )
    )
    add(n.tcap("Використані dunder methods"))
    add(
        table(
            ["Клас", "Dunder methods", "Призначення"],
            [
                [
                    "<code>Grade</code>",
                    "<code>__lt__ __str__ __post_init__</code>",
                    "порядок (total_ordering), вивід, нормалізація",
                ],
                [
                    "<code>Student</code>",
                    "<code>__eq__ __hash__ __str__ __post_init__</code>",
                    "тотожність за id, вивід, валідація",
                ],
                [
                    "<code>AcademicRecord</code>",
                    "<code>__len__ __iter__ __getitem__ __contains__ __repr__</code>",
                    "custom collection: len, for, record['Математика'], in",
                ],
                [
                    "<code>Group</code>",
                    "<code>__len__ __iter__ __contains__ __repr__</code>",
                    "<code>3 in group</code>, <code>for student in group</code>",
                ],
                [
                    "<code>InMemoryRepository</code>",
                    "<code>__len__ __iter__ __contains__ __getitem__</code>",
                    "<code>1 in repo</code>, <code>repo[key]</code>",
                ],
                [
                    "<code>GradingPolicy</code>",
                    "<code>__init_subclass__</code>",
                    "автоматична реєстрація підкласів у фабриці",
                ],
            ],
        )
    )

    add("<h1>6. Application service, dependency injection і SOLID</h1>")
    add(
        "<p><code>StudentService</code> отримує реєстр, notifier і політику через конструктор "
        "і залежить лише від абстракцій; конкретні класи створюються в одному місці – "
        "composition root (<code>build_registry</code>, <code>build_services</code>). Один "
        "реєстр можна під'єднати до сервісів із різними notifier.</p>"
    )
    add(
        src(
            services.StudentService.__init__,
            services.StudentService.register,
            main.build_registry,
            main.build_services,
        )
    )
    add(n.tcap("Принципи SOLID у моделі"))
    add(
        table(
            ["Принцип", "Де реалізовано"],
            [
                [
                    "SRP",
                    "<code>StudentRegistry</code> – інваріанти складу груп, <code>StudentService</code> "
                    "– сценарії та сповіщення, <code>ReportService</code> – звіти, "
                    "<code>GradingPolicy</code> – обчислення, <code>Grade</code> – валідація оцінки",
                ],
                [
                    "OCP",
                    "нова стратегія – новий підклас з <code>name=...</code>: фабрика, реєстр, звіти "
                    "не змінюються; новий канал сповіщень – новий клас із <code>send</code>",
                ],
                [
                    "LSP",
                    "обидва види студентів виконують контракт <code>Student</code>; усі стратегії "
                    "повертають <code>Grade | None</code> (None для порожнього запису) і взаємозамінні",
                ],
                [
                    "ISP",
                    "<code>Parser</code>, <code>Validator</code>, <code>Formatter</code> – окремі "
                    "протоколи; <code>Notifier</code> має один метод",
                ],
                [
                    "DIP",
                    "сервіси залежать від <code>Notifier</code> (Protocol), <code>GradingPolicy</code> "
                    "і <code>Repository</code> (ABC), а не від конкретних класів",
                ],
            ],
        )
    )

    add("<h1>7. Виконання програми</h1>")
    add(terminal("python -m domain_app.main", output))
    add(n.fcap("Виконання демонстраційного сценарію"))
    add(
        "<p>Перевірка вручну для Анни Коваль (90/5 кредитів, 95/6, 89.5/3): простий середній "
        "(90 + 95 + 89.5) / 3 = 91.50; зважений (90·5 + 95·6 + 89.5·3) / 14 = 92.04; "
        "середнє двох найкращих (95 + 90) / 2 = 92.50. Після переведення Максима до PI-22 "
        "середній бал групи PI-21 – (91.50 + 84.00 + 88.70) / 3 = 88.07, а Дмитро після "
        "перездачі математики на 70 має (70 + 62 + 59.7) / 3 = 63.90.</p>"
    )

    add("<h1>8. Статична перевірка типів (mypy)</h1>")
    add(
        "<p>Використано mypy зі <code>strict = true</code> (налаштування в "
        '<code>pyproject.toml</code>, <code>mypy_path = "src"</code>). Перевірка '
        "<code>src</code> і <code>tests</code> проходить без зауважень. Обов'язковий "
        "експеримент: у файл <code>experiments/type_errors.py</code> навмисно внесено три "
        "помилки з методички та чотири порушення доменного контракту:</p>"
    )
    add(terminal("mypy experiments/type_errors.py", errors))
    add(n.tcap("Знайдені помилки та виправлення (experiments/type_errors_fixed.py)"))
    add(
        table(
            ["№", "Помилка", "Виправлення"],
            [
                ["1", '<code>student_id: int = "1"</code>', "<code>student_id: int = 1</code>"],
                [
                    "2",
                    '<code>def total() -&gt; int: return "100"</code>',
                    "<code>return 100</code>",
                ],
                [
                    "3",
                    "<code>Group</code> у <code>InMemoryRepository[int, Student]</code>",
                    "окремий <code>InMemoryRepository[GroupCode, Group]</code>",
                ],
                [
                    "4",
                    "присвоєння <code>student.full_name</code> (property без setter)",
                    "<code>student.edit(first_name=...)</code>",
                ],
                ["5", "<code>Grade.of(91.5)</code> – float", '<code>Grade.of("91.5")</code>'],
                [
                    "6",
                    "екземпляр абстрактного <code>GradingPolicy</code>",
                    "<code>SimpleAverage()</code> з анотацією <code>GradingPolicy</code>",
                ],
                [
                    "7",
                    "ключ <code>str</code> для constrained <code>K</code>",
                    "<code>InMemoryRepository[int, Student]</code>",
                ],
            ],
        )
    )
    add(terminal("mypy experiments/type_errors_fixed.py experiments/di_comparison.py", fixed))
    add(terminal("mypy   # src і tests, strict", strict))

    add("<h1>9. Експериментальна частина</h1>")
    add(
        "<p><b>Dependency injection.</b> Варіант A (<code>HardwiredStudentService</code>) сам "
        "створює реєстр і <code>ConsoleNotifier</code>; варіант B – "
        "<code>StudentService</code> з DI. Обидва виконують однакову реєстрацію студента:</p>"
    )
    add(terminal("python experiments/di_comparison.py", di))
    add(n.tcap("Порівняння варіантів A і B"))
    add(
        table(
            ["Критерій", "A: залежність усередині", "B: dependency injection"],
            [
                [
                    "тестування",
                    "лише перехопленням stdout і розбором тексту",
                    "<code>MemoryNotifier</code>: повідомлення доступні як дані",
                ],
                ["заміна", "зміна коду класу", "інший об'єкт у конструкторі"],
                ["DIP", "порушено: залежить від конкретних класів", "виконано: Protocol і ABC"],
                ["coupling", "2 конкретні класи всередині сервісу", "0 – лише абстракції"],
            ],
        )
    )
    add(
        "<p><b>Inheritance vs composition.</b> Обробку рядка студента (parse → validate → format, "
        "формат ЛР3) реалізовано двома способами: <code>CsvRowProcessor</code> успадковує "
        "template method від <code>BaseRowProcessor</code>, а <code>RowProcessor(parser, "
        "validator, formatter)</code> складається з трьох компонентів-протоколів; обидва дають "
        "однаковий результат (перевірено тестом).</p>"
    )
    add(n.tcap("Порівняння inheritance і composition"))
    add(
        table(
            ["Критерій", "Inheritance", "Composition"],
            [
                [
                    "coupling",
                    "підклас залежить від деталей template method базового класу",
                    "процесор знає лише три протоколи",
                ],
                [
                    "extensibility",
                    "n форматів × m форматувань = n·m підкласів",
                    "n + m незалежних класів (2 parsers + 2 formatters = 4 комбінації)",
                ],
                [
                    "testability",
                    "тестується лише весь процесор",
                    "кожен компонент тестується окремо, решту можна підмінити",
                ],
                [
                    "reuse",
                    "форматування прив'язане до ієрархії",
                    "<code>ShortFormatter</code> працює з будь-яким parser",
                ],
            ],
        )
    )

    add("<h1>10. Перевірка правильності</h1>")
    add(
        f"<p>{total_tests} тестів (unittest) перевіряють value objects і їх межі, стратегії "
        "оцінювання на відомих даних, фабрику, custom collection, entity-рівність, поліморфну "
        "стипендію, групу, generic-репозиторій, реєстр (дублікати, переведення, найкращий), "
        "сервіси з <code>MemoryNotifier</code>, звіти, TypedDict, runtime_checkable Protocol, "
        "рівність результатів inheritance і composition та весь демонстраційний сценарій. Усі "
        "перевірки запускає CI-like команда:</p>"
    )
    add(terminal("python tools/check.py", checks))

    add("<h1>Висновки</h1>")
    add(
        "<p>Побудовано типізовану об'єктну модель системи обліку студентів: entity "
        "<code>Student</code> з двома підкласами, група й академічний запис як колекції, value "
        "objects <code>Grade</code>, <code>GroupCode</code>, <code>CourseResult</code>, ABC-стратегії "
        "оцінювання з фабрикою, generic-репозиторій, Protocol для сповіщень і application "
        "services із dependency injection. Наслідування використано лише для справжнього is-a, "
        "решту поведінки зібрано композицією, що підтвердило порівняння: DI і композиція "
        "зменшують coupling і спрощують тестування. mypy у strict-режимі знайшов усі 7 "
        "навмисних помилок, а код проєкту й тестів проходить перевірку без зауважень.</p>"
    )

    body = keep_numbers_together("\n".join(parts))
    return (
        "<!doctype html><html lang='uk'><head><meta charset='utf-8'>"
        f"<title>Звіт ЛР4</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


def print_pdf(html_path: Path, pdf_path: Path, profile: Path) -> None:
    args = [
        str(EDGE),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    subprocess.run(args, check=True, capture_output=True, timeout=120)


def main_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument(
        "--profile", type=Path, default=Path(tempfile.gettempdir()) / "lab4_report_edge_profile"
    )
    args = parser.parse_args()

    html_path = REPORT_DIR / "report.html"
    html_path.write_text(build_html(args.venv), encoding="utf-8")
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    print_pdf(html_path, PDF_PATH, args.profile)

    import pymupdf

    with pymupdf.open(PDF_PATH) as document:
        print(f"PDF: {PDF_PATH} — {document.page_count} сторінок")


if __name__ == "__main__":
    main_cli()
