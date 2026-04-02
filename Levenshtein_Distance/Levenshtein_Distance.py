import reflex as rx
from typing import Any
from .engine import compare_records, TEXT_SIMILARITY, EXACT_MATCH, DATE_PARTS

class SinglePageState(rx.State):
    # Weights configuration
    w_first_name: str = "30"
    w_last_name: str = "30"
    w_dob: str = "20"
    w_gender: str = "20"
    
    # Source A
    a_first_name: str = ""
    a_last_name: str = ""
    a_dob: str = ""
    a_gender: str = ""
    
    # Source B
    b_first_name: str = ""
    b_last_name: str = ""
    b_dob: str = ""
    b_gender: str = ""
    
    # Results
    has_results: bool = False
    aggregate_score: str = "0.0"
    
    # List of dictionaries for the table
    results_list: list[dict[str, str]] = []
    
    def run_comparison(self):
        field_configs = [
            {"key": "first_name", "label": "FIRST NAME", "comparator": TEXT_SIMILARITY, "weight": float(self.w_first_name or 0), "active": True},
            {"key": "last_name", "label": "LAST NAME", "comparator": TEXT_SIMILARITY, "weight": float(self.w_last_name or 0), "active": True},
            {"key": "dob", "label": "DATE OF BIRTH", "comparator": DATE_PARTS, "weight": float(self.w_dob or 0), "active": True},
            {"key": "gender", "label": "GENDER", "comparator": EXACT_MATCH, "weight": float(self.w_gender or 0), "active": True},
        ]
        
        record_a = {
            "first_name": self.a_first_name,
            "last_name": self.a_last_name,
            "dob": self.a_dob,
            "gender": self.a_gender
        }
        
        record_b = {
            "first_name": self.b_first_name,
            "last_name": self.b_last_name,
            "dob": self.b_dob,
            "gender": self.b_gender
        }
        
        mapping = {k: k for k in record_a.keys()}
        
        try:
            res = compare_records("manual", record_a, record_b, field_configs, mapping, mapping)
        except Exception:
            return

        self.aggregate_score = f"{res.overall_score:.1f}"
        
        rows = []
        for b in res.breakdowns:
            sim_percentage = (b.score / b.max_score) * 100 if b.max_score else 0.0
            rows.append({
                "attribute": b.label,
                "a_val": b.left_value or "-",
                "b_val": b.right_value or "-",
                "sim": f"{sim_percentage:.2f}",
                "weighted": f"{b.score:.2f}"
            })
        self.results_list = rows
        self.has_results = True


def section_header(title: str) -> rx.Component:
    return rx.text(
        title, 
        color="#737373", 
        font_size="0.85rem", 
        font_weight="500",
        letter_spacing="0.15em", 
        margin_bottom="2rem"
    )

def underlined_input(value_bind, on_change_bind, placeholder="") -> rx.Component:
    return rx.input(
        value=value_bind,
        on_change=on_change_bind,
        placeholder=placeholder,
        radius="none",
        border="none",
        border_bottom="1px solid #27272A",
        background="transparent",
        color="#FAFAFA",
        _focus={"outline": "none", "border_bottom": "1px solid #FAFAFA"},
        padding_x="0",
        padding_y="0.5rem",
        font_size="1.1rem",
        width="100%",
        height="5%",
    )

def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Top-right sticky/upload mock button
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.icon("upload", size=18), 
                    "UPLOAD DATASET", 
                    variant="outline", 
                    color_scheme="gray", 
                    color="#A1A1AA", 
                    radius="none",
                    border="1px solid #27272A",
                    _hover={"background": "#1A1A1A", "color": "#FAFAFA"}
                ),
                width="100%",
                padding_y="1rem"
            ),
            
            # --- 01 WEIGHT CONFIGURATION ---
            section_header("01 // WEIGHT CONFIGURATION"),
            rx.hstack(
                rx.vstack(
                    rx.text("FIRST NAME", size="1", color="#737373", letter_spacing="0.05em"), 
                    underlined_input(SinglePageState.w_first_name, SinglePageState.set_w_first_name), 
                    width="100%", spacing="1"
                ),
                rx.vstack(
                    rx.text("LAST NAME", size="1", color="#737373", letter_spacing="0.05em"), 
                    underlined_input(SinglePageState.w_last_name, SinglePageState.set_w_last_name), 
                    width="100%", spacing="1"
                ),
                rx.vstack(
                    rx.text("DATE OF BIRTH", size="1", color="#737373", letter_spacing="0.05em"), 
                    underlined_input(SinglePageState.w_dob, SinglePageState.set_w_dob), 
                    width="100%", spacing="1"
                ),
                rx.vstack(
                    rx.text("GENDER", size="1", color="#737373", letter_spacing="0.05em"), 
                    underlined_input(SinglePageState.w_gender, SinglePageState.set_w_gender), 
                    width="100%", spacing="1"
                ),
                spacing="6",
                width="100%",
                margin_bottom="5rem",
            ),
            
            # --- 02 MANUAL COMPARISON ---
            section_header("02 // MANUAL COMPARISON"),
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.box(width="6px", height="6px", background="#FAFAFA"), 
                        rx.text("SOURCE_A", color="#FAFAFA", font_weight="600", font_size="0.85rem", letter_spacing="0.1em")
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("FIRST NAME", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.a_first_name, SinglePageState.set_a_first_name, "e.g. Jonathan"), 
                        width="100%", spacing="1"
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("LAST NAME", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.a_last_name, SinglePageState.set_a_last_name, "e.g. Muller"), 
                        width="100%", spacing="1"
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("DOB", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.a_dob, SinglePageState.set_a_dob, "YYYY-MM-DD"), 
                        width="100%", spacing="1"
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("GENDER", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.a_gender, SinglePageState.set_a_gender, "M/F"), 
                        width="100%", spacing="1"
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.box(width="6px", height="6px", border="1px solid #FAFAFA"), 
                        rx.text("SOURCE_B", color="#FAFAFA", font_weight="600", font_size="0.85rem", letter_spacing="0.1em")
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("FIRST NAME", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.b_first_name, SinglePageState.set_b_first_name, "e.g. John"), 
                        width="100%", spacing="1"
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("LAST NAME", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.b_last_name, SinglePageState.set_b_last_name, "e.g. Miller"), 
                        width="100%", spacing="1"
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("DOB", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.b_dob, SinglePageState.set_b_dob, "YYYY-MM-DD"), 
                        width="100%", spacing="1"
                    ),
                    rx.box(height="1rem"),
                    rx.vstack(
                        rx.text("GENDER", size="1", color="#737373", letter_spacing="0.05em"), 
                        underlined_input(SinglePageState.b_gender, SinglePageState.set_b_gender, "M/F"), 
                        width="100%", spacing="1"
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="8",
                width="100%",
                margin_bottom="4rem"
            ),
            
            rx.center(
                rx.button(
                    "RUN COMPARISON", 
                    on_click=SinglePageState.run_comparison, 
                    background="#FAFAFA", 
                    color="#0A0A0A", 
                    radius="none", 
                    font_weight="bold", 
                    letter_spacing="0.1em", 
                    padding="1.8rem 4rem",
                    _hover={"opacity": 0.8}
                ),
                width="100%",
                margin_bottom="5rem"
            ),
            
            # --- 03 ANALYSIS RESULTS ---
            rx.cond(
                SinglePageState.has_results,
                rx.vstack(
                    section_header("03 // ANALYSIS RESULTS"),
                    # Table Header
                    rx.hstack(
                        rx.text("ATTRIBUTE", width="20%", color="#737373", font_size="0.75rem", letter_spacing="0.05em"),
                        rx.text("SOURCE A", width="25%", color="#737373", font_size="0.75rem", letter_spacing="0.05em"),
                        rx.text("SOURCE B", width="25%", color="#737373", font_size="0.75rem", letter_spacing="0.05em"),
                        rx.text("SIMILARITY (%)", width="15%", color="#737373", font_size="0.75rem", text_align="right", letter_spacing="0.05em"),
                        rx.text("WEIGHTED", width="15%", color="#737373", font_size="0.75rem", text_align="right", letter_spacing="0.05em"),
                        width="100%",
                        border_bottom="1px solid #1A1A1A",
                        padding_bottom="1rem",
                        margin_bottom="1rem"
                    ),
                    # Table Body
                    rx.foreach(
                        SinglePageState.results_list,
                        lambda row: rx.hstack(
                            rx.text(row["attribute"], width="20%", color="#FAFAFA", font_weight="600", font_size="0.9rem"),
                            rx.text(row["a_val"], width="25%", color="#A1A1AA", font_size="0.9rem"),
                            rx.text(row["b_val"], width="25%", color="#A1A1AA", font_size="0.9rem"),
                            rx.text(row["sim"], width="15%", color="#FAFAFA", font_weight="600", font_size="0.9rem", text_align="right"),
                            rx.text(row["weighted"], width="15%", color="#FAFAFA", font_weight="600", font_size="0.9rem", text_align="right"),
                            width="100%",
                            padding_y="0.75rem"
                        )
                    ),
                    
                    rx.divider(margin_top="3rem", margin_bottom="2rem", border_color="#1A1A1A"),
                    
                    # Aggregate Score
                    rx.vstack(
                        rx.text("AGGREGATE SIMILARITY INDEX", color="#737373", font_size="0.75rem", letter_spacing="0.1em"),
                        rx.hstack(
                            rx.text(SinglePageState.aggregate_score, font_size="6rem", font_weight="300", line_height="1", color="#FAFAFA"),
                            rx.text("%", font_size="2rem", color="#737373", align_self="end", padding_bottom="1rem"),
                            spacing="2",
                        ),
                        align_items="end",
                        width="100%"
                    ),
                    width="100%"
                ),
                rx.box()
            ),
            
            # Bottom Padding
            rx.box(height="5rem"),
            
            width="100%",
            max_width="1000px",
            margin="0 auto"
        ),
        background="#0A0A0A",
        min_height="100vh",
        padding_x=["1.5rem", "2rem", "5%"],
        font_family="'Inter', sans-serif"
    )

app = rx.App(theme=rx.theme(appearance="dark", radius="none", accent_color="gray"))
app.add_page(index, route="/", title="Similarity Checker")
