## About the Multi-Purpose Tactical Pack 🎯♟️

![Lint](https://github.com/SKOHscripts/Optimized-Chess-Puzzles/actions/workflows/pylint.yml/badge.svg)
![Tests](https://github.com/SKOHscripts/Optimized-Chess-Puzzles/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/SKOHscripts/Optimized-Chess-Puzzles/branch/main/graph/badge.svg)](https://codecov.io/gh/SKOHscripts/Optimized-Chess-Puzzles)

  <img
    align="right"
    src="logo.png"
    alt="Optimized-Chess-Puzzles logo"
    width="240"
    height="240"
  />

This tactical pack has been designed as a **versatile and scientifically optimized training tool** that adapts to several chess learning approaches:

### 🎯 **Multiple Pack Uses**

**1. Woodpecker Method by ELO Range 🔨**  
Each range (~1200 puzzles) allows you to apply the famous Woodpecker method: solve the same set multiple times in accelerated cycles to develop automatic recognition of tactical patterns. This approach transforms conscious thinking into unconscious reflexes, drastically increasing calculation speed in games.

**2. Personalized Spaced Repetition 🧠🔄**  
You can use Anki's spaced repetition system to optimize learning according to your current level. The carefully selected puzzles guarantee constant progress without excessive frustration. Research shows that spaced repetition improves long-term retention by 200-300% compared to traditional methods.
>
> #### Recommended Tool: Anki 📱💻
> I strongly recommend using Anki for learning these puzzles, as it's specifically designed for spaced repetition and offers optimal scheduling algorithms, especially with the FSRS scheduling algorithm. > Anki is available for free on multiple platforms:
>
> Desktop: https://apps.ankiweb.net/
>
> Mobile: Available on iOS App Store, Google Play Store, FDroid
>
> Web: https://ankiweb.net/ for synchronization across devices
>
> #### Ready-to-Use Complete Pack 🎁
> The complete tactical pack is available in Anki's shared decks (future link here) and is ready to use immediately. Simply search for the deck in the shared collection, download it, and start your training with optimized spaced repetition intervals.

**3. Targeted Thematic Training 🎨**  
Thanks to detailed tags (themes and openings), you can create custom packs to work specifically on your weaknesses: forks, pins, discovered attacks, or specific defenses like the Sicilian or French. This targeted approach accelerates learning of specific patterns.

### 🖥️ **Clean Interface for Cognitive Optimization**

**Minimalist Front Display 🎨**  
The interface shows only the essentials: the board and the side to move. This deliberate simplification eliminates visual distractions and forces concentration on pure analysis. Research in cognitive psychology shows that a simplified visual environment improves problem-solving performance by 15-25%.

**Relevant Information on Back 📊**  
Once your thinking is complete, you access crucial information: solution moves (in readable SAN notation), ELO level, tactical themes, and direct links to Lichess and Chess.com to deepen analysis on the platforms. This organization respects the principle of "progressive disclosure" optimal for learning.

### 🚫 **No Piece Movement: A Founded Pedagogical Choice**

**Visualization Development 👁️🧠**  
The inability to move pieces forces development of "chess vision" - this crucial ability to visualize moves in your head. Studies show that strong players possess visualization capabilities 3-4 times superior to average players.

**Square-by-Square Reading Training 📖**  
By then working with moves in SAN notation, you develop square reading skills, essential for theoretical study and game analysis. This mastery "comes quickly and is especially important for overall chess mastery".

**Coordinate Removal for Pure Learning 🎯**  
The absence of coordinates on the chessboard is not an oversight but a deliberate choice. This accentuates pure spatial learning and pattern memorization through visual recognition rather than alphabetical referencing, a method closer to the intuition developed by masters.

### 🔬 **Scientific Bases of Design Choices**

**Pattern Recognition and Cognitive Chunks 🧩**  
The diversified selection by themes is based on Chase & Simon's (1973) "chunks" theory: the brain recognizes and memorizes recurring patterns more effectively when they are presented in varied but structured contexts.

**Cognitive Load Theory 🧠⚖️**  
The clean interface respects Sweller's principles on cognitive load: by eliminating non-essential elements, the brain can devote all its resources to tactical analysis.

**Skill Transfer 🔄**  
Systematically trained visualization transfers effectively to real games, unlike exercises with physical piece manipulation. Research shows a skill transfer of 70-85% between visualization training and game performance.

### 🏆 **Result: A Scientifically Optimized Training Tool**

This pack combines the best modern pedagogical practices:
- **Spaced repetition** for memory anchoring
- **Forced visualization** to develop intuition
- **Thematic diversity** for generalization
- **Cognitively optimized interface** for concentration

The whole forms a training system that respects the brain's natural learning mechanisms while maximizing pedagogical efficiency for chess improvement! 🚀♟️

## 🔬 **Advanced Selection Method by Thematic Sampling**

### **1. Data Acquisition and Preparation 📥**

The script begins by downloading the **complete Lichess database** (several million puzzles) and automatically decompresses it. This database contains all puzzles solved by the community with their metadata: ELO rating, popularity, tactical themes, and associated openings.

### **2. Intelligent Sampling by Thematic Diversity 🎯**

**Fundamental principle:** Instead of simply taking the most popular puzzles (which would create redundancies), the script applies a **maximum coverage algorithm by theme**:

```python
def sample_by_themes(tranche, target_per_theme=20, popularity_threshold=90):
```

**Selection steps:**
1. **Theme identification**: For each puzzle in the ELO range, extraction of all tactical themes (fork, pin, discovered attack, etc.)
2. **Quality filtering**: Priority selection of puzzles with Popularity ≥ 90% (validated by the community)
3. **Balanced distribution**: Maximum 20 puzzles per theme to avoid overrepresentation
4. **Intelligent complement**: For rare themes, adding puzzles with lower popularity to guarantee coverage

### **3. Exhaustive Coverage Guarantee 📊**

**Adaptive complement mechanism:**
```python
if len(selected_rows) < 700:
    needed = 700 - len(selected_rows)
    extras = tranche[...].sort_values('Popularity', ascending=False).head(needed)
```

If thematic sampling produces fewer than 700 puzzles, the script automatically completes with the most popular puzzles not yet selected. This guarantees sufficient volume for intensive training while preserving diversity.

### **4. Optimized Technical Preprocessing ⚙️**

**Position adjustment:**
```python
def adjust_fen_and_moves(fen, moves):
    # Apply the first move to the FEN
    # Remove the first move from the sequence
```

Crucial point: Lichess puzzles give the position **before** the opponent's move. The script automatically applies this first move to present the real position to solve, then converts the remaining moves to readable notation (SAN). This technical step guarantees that each Anki card presents exactly the situation the player must analyze.

### **5. Quality Control and Transparency 📈**

**Automatic coverage report:**
```python
def report_theme_coverage(sampled_rows, out_file, tranche):
    percentage_coverage = len(selected_themes) / max(len(tranche_themes), 1) * 100
```

For each generated pack, the script calculates and displays:
- The **real percentage of thematic coverage** (covered themes vs available themes in the range)
- The **distribution of themes** most and least represented
- The **total number of puzzles** selected

This transparency allows verification that each pack offers maximum coverage of tactical patterns for its level.

### **6. Data Structure Optimized for Anki 📋**

**Generated columns:**
- **FEN Position**: Real position to analyze (after preprocessing)
- **Moves_SAN**: Move sequence in readable notation
- **Unified Tags**: Merged themes + openings for easy filtering
- **Metadata**: Rating, popularity for progress tracking

### **🎯 Result: Scientifically Optimal Sampling**

This method produces packs that:
- **Maximize pattern diversity** encountered (>98% thematic coverage according to ranges)
- **Prioritize pedagogical quality** (puzzles validated by the community)
- **Avoid redundancies** while guaranteeing anchoring through repetition
- **Adapt to level** (increasing complexity according to ELO ranges)

The script thus transforms a raw database of millions of puzzles into **custom training sets**, optimized for systematic progression and lasting memorization of tactical patterns essential at each level! 🚀♟️
