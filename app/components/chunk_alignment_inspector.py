import streamlit as st
import difflib

def render_chunk_alignment_inspector(chunk_a: str, chunk_b: str, score: float):
    """
    Renders a side-by-side chunk alignment inspector with highlighted matching words.
    """
    st.markdown("### Chunk Alignment Inspector")
    
    # Display similarity score badge
    badge_color = "red" if score > 0.8 else ("orange" if score > 0.5 else "green")
    st.markdown(f"**Similarity Score:** :{badge_color}[{score:.2%}]")
    
    if not chunk_a and not chunk_b:
        st.info("Both chunks are empty.")
        return
        
    words_a = chunk_a.split()
    words_b = chunk_b.split()
    
    sm = difflib.SequenceMatcher(None, words_a, words_b)
    
    html_a = []
    html_b = []
    
    # Yellow for identical, light blue for replace (paraphrased)
    highlight_match = "background-color: #ffeb3b; color: black; font-weight: bold; border-radius: 3px; padding: 0 2px;"
    highlight_similar = "background-color: #bbdefb; color: black; border-radius: 3px; padding: 0 2px;"
    
    for opcode, i1, i2, j1, j2 in sm.get_opcodes():
        if opcode == 'equal':
            html_a.append(f"<span style='{highlight_match}'>{' '.join(words_a[i1:i2])}</span>")
            html_b.append(f"<span style='{highlight_match}'>{' '.join(words_b[j1:j2])}</span>")
        elif opcode == 'replace':
            html_a.append(f"<span style='{highlight_similar}'>{' '.join(words_a[i1:i2])}</span>")
            html_b.append(f"<span style='{highlight_similar}'>{' '.join(words_b[j1:j2])}</span>")
        elif opcode == 'delete':
            html_a.append(f"<span>{' '.join(words_a[i1:i2])}</span>")
        elif opcode == 'insert':
            html_b.append(f"<span>{' '.join(words_b[j1:j2])}</span>")
            
    text_a = " ".join(html_a)
    text_b = " ".join(html_b)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Document A Chunk**")
        st.markdown(f"<div style='padding: 10px; border: 1px solid #ddd; border-radius: 5px; height: 100%; min-height: 200px;'>{text_a}</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("**Document B Chunk**")
        st.markdown(f"<div style='padding: 10px; border: 1px solid #ddd; border-radius: 5px; height: 100%; min-height: 200px;'>{text_b}</div>", unsafe_allow_html=True)
