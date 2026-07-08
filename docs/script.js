document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Terminal Typewriter Animation ---
    const terminalLines = [
        { text: "$ sirius-init init my_saas --csv users.csv --theme violet", class: "term-cmd", delay: 800 },
        { text: "Analyzing schema structure...", class: "term-info", delay: 500 },
        { text: "Scaffolding project in: ./my_saas (Theme: violet, Port: 8000, DB: sqlite)", class: "term-info", delay: 200 },
        { text: "Initializing Alembic migration system...", class: "term-info", delay: 600 },
        { text: "Autogenerating migration scripts...", class: "term-info", delay: 800 },
        { text: "Running database migrations...", class: "term-info", delay: 1000 },
        { text: "[OK] Alembic migration system initialized successfully!", class: "term-success", delay: 200 },
        { text: "Seeding initial data from source files...", class: "term-info", delay: 400 },
        { text: "[OK] Database seeded successfully!", class: "term-success", delay: 300 },
        { text: "\n[SUCCESS] Project 'my_saas' has been created.", class: "term-success", delay: 100 }
    ];

    const terminalContainer = document.getElementById('typewriter-container');
    
    async function typeTerminal() {
        terminalContainer.innerHTML = ''; // Reset
        
        for (const line of terminalLines) {
            await new Promise(r => setTimeout(r, line.delay));
            
            const div = document.createElement('div');
            div.className = `term-line ${line.class}`;
            terminalContainer.appendChild(div);
            
            // Typewriter effect for the command line
            if (line.class === 'term-cmd') {
                for (let i = 0; i < line.text.length; i++) {
                    div.textContent += line.text[i];
                    await new Promise(r => setTimeout(r, 30)); // typing speed
                }
            } else {
                div.textContent = line.text;
            }
        }
        
        // Loop animation after a delay
        setTimeout(typeTerminal, 5000);
    }
    
    // Start terminal animation
    setTimeout(typeTerminal, 500);


    // --- 2. Copy to Clipboard functionality ---
    const copyBtns = document.querySelectorAll('.copy-btn');
    
    copyBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const targetId = btn.getAttribute('data-target');
            const codeBlock = document.getElementById(targetId);
            
            if (codeBlock) {
                try {
                    await navigator.clipboard.writeText(codeBlock.innerText);
                    
                    // Visual feedback
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                    
                    setTimeout(() => {
                        btn.innerHTML = originalHTML;
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy text: ', err);
                }
            }
        });
    });


    // --- 3. Tabs Switching Logic ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active classes
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked
            btn.classList.add('active');
            
            // Show corresponding content
            const targetTab = btn.getAttribute('data-tab');
            document.getElementById(`tab-${targetTab}`).classList.add('active');
        });
    });
});
