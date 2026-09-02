
// function to switch tabs in product
function initializeModalComponents() {
    console.log('initializeModalComponents');
    //   function initTabs() {
    //     const tabs = document.querySelectorAll('.tabs-list li');
    //     const tabContents = document.querySelectorAll('.tabs-content-wrapper .tab');
    
    //     function activateTab(targetId) {
    //       tabs.forEach(tab => tab.classList.remove('active'));
    //       tabContents.forEach(content => content.classList.remove('active'));
    
    //       const targetTab = document.querySelector(`a[href="${targetId}"]`).parentElement;
    //       const targetContent = document.querySelector(targetId);
    //       targetTab?.classList.add('active');
    //       targetContent?.classList.add('active');
    //     }
    
    //     tabs.forEach(tab => {
    //       tab.addEventListener('click', function(e) {
    //         e.preventDefault();
    //         const targetId = this.querySelector('a').getAttribute('href');
    //         activateTab(targetId);
            
    //         if (swiper) {
    //           swiper.update();
    //         }
    //       });
    //     });
    
    //     if (tabs.length > 0 && !window.location.hash) {
    //       activateTab(tabs[0].querySelector('a').getAttribute('href'));
    //     }
    //   }
    
      let swiper;
      if (document.querySelector('.tabs-block.swiper-container')) {
        if (swiper) {
          swiper.destroy();
        }
        
        swiper = new Swiper('.tabs-block.swiper-container', {
          slidesPerView: 'auto',
          spaceBetween: 20,
          navigation: {
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
          },
        });
      }
      const relatedSwiper = new Swiper('.featured-carousel', {
        slidesPerView: 'auto',
        spaceBetween: 30,
        navigation: {
          nextEl: '.featured-carousel .swiper-button-next',
          prevEl: '.featured-carousel .swiper-button-prev',
        },
        breakpoints: {
          320: { slidesPerView: 1 },
          768: { slidesPerView: 2 },
          1024: { slidesPerView: 3 }
        }
      });
      console.log('swiper', relatedSwiper);
  
      document.querySelectorAll('.featured-item').forEach(item => {
        item.addEventListener('click', function(e) {
          e.preventDefault();
          const Url = this.dataset.href;
          const newUrl = window.location.origin + Url;
          loadProductModal(newUrl);
        });
      });
    
      initTabs();
    }
  