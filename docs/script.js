document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Theme Toggle Logic ---
    const themeBtn = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    
    // SVG Icons
    const sunIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
    const moonIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;

    // Load saved theme or default to light
    const savedTheme = localStorage.getItem('sirius-theme') || 'light';
    htmlEl.setAttribute('data-theme', savedTheme);
    themeBtn.innerHTML = savedTheme === 'light' ? moonIcon : sunIcon;

    themeBtn.addEventListener('click', () => {
        const currentTheme = htmlEl.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        htmlEl.setAttribute('data-theme', newTheme);
        localStorage.setItem('sirius-theme', newTheme);
        
        themeBtn.innerHTML = newTheme === 'light' ? moonIcon : sunIcon;
    });

    // --- 2. Copy to Clipboard ---
    const copyBtns = document.querySelectorAll('.copy-btn');
    
    copyBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            // Find the <code> element inside the same .code-block container
            const codeBlock = btn.parentElement.querySelector('code');
            
            if (codeBlock) {
                try {
                    await navigator.clipboard.writeText(codeBlock.innerText);
                    
                    const originalText = btn.innerText;
                    btn.innerText = 'Copied!';
                    btn.style.color = '#10B981';
                    btn.style.borderColor = '#10B981';
                    
                    setTimeout(() => {
                        btn.innerText = originalText;
                        btn.style.color = '';
                        btn.style.borderColor = '';
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy text: ', err);
                }
            }
        });
    });

    // --- 3. Scrollspy (Highlight active sidebar link) ---
    const sections = document.querySelectorAll('section, h3[id]');
    const navLinks = document.querySelectorAll('.nav-link');

    window.addEventListener('scroll', () => {
        let current = '';
        const scrollY = window.pageYOffset;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            // Adjust offset to trigger highlight slightly before the section hits the top
            if (scrollY >= (sectionTop - 150)) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').includes(current) && current !== '') {
                link.classList.add('active');
            }
        });
    });
});
