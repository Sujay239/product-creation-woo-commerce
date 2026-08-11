<?php
/**
 * WooCommerce Single Product Gallery:
 * - Auto-slide + Infinite loop + Bullet pagination on initial load and Simple Products.
 * - On Variation Click: Stops auto-slide, displays the variation image, and hides bullet pagination.
 * - On Variation Clear: Restores the parent product image, restores bullet pagination, and resumes auto-slide.
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

// -------------------------------------------------------------
// 1. FlexSlider Carousel Options
// -------------------------------------------------------------
add_filter('woocommerce_single_product_carousel_options', function ($options) {
    $options['animation']       = 'slide';
    $options['animationLoop']   = true;   // Infinite loop
    $options['slideshow']       = true;   // Auto slide ON
    $options['slideshowSpeed']  = 3000;   // 3 seconds per slide
    $options['animationSpeed']  = 600;    // Transition speed
    $options['controlNav']      = true;   // Bullet pagination ON
    $options['directionNav']    = false;  // Previous/Next arrows OFF
    $options['smoothHeight']    = true;
    $options['touch']           = true;
    $options['pauseOnHover']    = true;

    return $options;
}, 9999);


// -------------------------------------------------------------
// 2. Custom CSS for Bullet Pagination & Gallery Layout
// -------------------------------------------------------------
add_action('wp_head', function () {
    if (!is_product()) return;
    ?>
    <style>
        /* Hide default thumbnail strip */
        .single-product .woocommerce-product-gallery .flex-control-thumbs {
            display: none !important;
        }

        /* Remove Previous / Next navigation completely */
        .single-product .woocommerce-product-gallery .flex-direction-nav,
        .single-product .woocommerce-product-gallery .flex-direction-nav li,
        .single-product .woocommerce-product-gallery .flex-direction-nav a {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
        }

        /* Bullet pagination container */
        .single-product .woocommerce-product-gallery .flex-control-paging {
            display: flex !important;
            justify-content: center;
            align-items: center;
            gap: 9px;
            list-style: none !important;
            margin: 14px 0 0 !important;
            padding: 0 !important;
            transition: opacity 0.25s ease, visibility 0.25s ease;
        }

        .single-product .woocommerce-product-gallery .flex-control-paging li {
            margin: 0 !important;
            padding: 0 !important;
            list-style: none !important;
            width: auto !important;
        }

        /* Bullet dot styles */
        .single-product .woocommerce-product-gallery .flex-control-paging li a {
            width: 8px !important;
            height: 8px !important;
            display: block !important;
            border-radius: 50% !important;
            background: #cfcfcf !important;
            border: none !important;
            font-size: 0 !important;
            text-indent: -9999px !important;
            overflow: hidden !important;
            cursor: pointer;
            transition: all 0.25s ease;
        }

        .single-product .woocommerce-product-gallery .flex-control-paging li a.flex-active {
            background: #111 !important;
            transform: scale(1.25);
        }

        /* Hide bullet dots when variation image is active */
        .single-product .woocommerce-product-gallery.variation-selected .flex-control-paging {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

        @media (max-width: 767px) {
            .single-product .woocommerce-product-gallery .flex-control-paging {
                margin-top: 12px !important;
            }

            .single-product .woocommerce-product-gallery .flex-control-paging li a {
                width: 7px !important;
                height: 7px !important;
            }
        }
    </style>
    <?php
});


// -------------------------------------------------------------
// 3. JavaScript: Guaranteed Auto-Slide & Variation Image Switcher
// -------------------------------------------------------------
add_action('wp_footer', function () {
    if (!is_product()) return;
    ?>
    <script type="text/javascript">
    jQuery(document).ready(function ($) {
        var $gallery = $('.woocommerce-product-gallery');
        var $form = $('form.variations_form');

        if (!$gallery.length) return;

        var autoSlideTimer = null;
        var slideDelay = 3000; // 3 seconds
        var isVariationActive = false;

        // 1. Capture original parent main image details on page load
        var $firstImg = $gallery.find('.woocommerce-product-gallery__image:first-child img, img.wp-post-image').first();
        var originalData = {
            src: $firstImg.attr('src') || '',
            srcset: $firstImg.attr('srcset') || '',
            large: $firstImg.attr('data-large_image') || '',
            href: $firstImg.closest('a').attr('href') || ''
        };

        // Helper: Start / Resume Auto Slide Timer
        function startAutoSlide() {
            stopAutoSlide();
            if (isVariationActive) return;

            // Try Flexslider play first
            try {
                $gallery.flexslider('play');
            } catch (e) {
                var fs = $gallery.data('flexslider');
                if (fs) fs.play();
            }

            // Also maintain custom interval backup to guarantee auto-sliding
            autoSlideTimer = setInterval(function () {
                if (isVariationActive) return;
                var totalSlides = $gallery.find('.woocommerce-product-gallery__wrapper > .woocommerce-product-gallery__image').length;
                if (totalSlides > 1) {
                    try {
                        $gallery.flexslider('next');
                    } catch (e) {
                        var fs = $gallery.data('flexslider');
                        if (fs) fs.flexAnimate(fs.getTarget('next'));
                    }
                }
            }, slideDelay);
        }

        // Helper: Stop / Pause Auto Slide Timer
        function stopAutoSlide() {
            if (autoSlideTimer) {
                clearInterval(autoSlideTimer);
                autoSlideTimer = null;
            }
            try {
                $gallery.flexslider('pause');
            } catch (e) {
                var fs = $gallery.data('flexslider');
                if (fs) fs.pause();
            }
        }

        // Start auto-slide on page load
        setTimeout(function () {
            startAutoSlide();
        }, 500);

        // Pause on mouse hover & resume on mouse leave (if no variation active)
        $gallery.on('mouseenter', function () {
            if (!isVariationActive) stopAutoSlide();
        }).on('mouseleave', function () {
            if (!isVariationActive) startAutoSlide();
        });

        // -------------------------------------------------------------
        // 2. When a Variation is Selected
        // -------------------------------------------------------------
        if ($form.length) {
            $form.on('found_variation show_variation', function (event, variation) {
                if (!variation || !variation.image || !variation.image.src) return;

                var customSrc = variation.image.src;
                if (customSrc === '' || variation.image.is_placeholder) return;

                isVariationActive = true;
                stopAutoSlide();

                // Move slider to slide 0
                try {
                    $gallery.flexslider(0);
                } catch (e) {
                    var fs = $gallery.data('flexslider');
                    if (fs) fs.flexAnimate(0);
                }

                // Update visible images & clones with variation image
                $gallery.find('.woocommerce-product-gallery__image:first-child img, .clone:first-child img, .flex-active-slide img').each(function () {
                    $(this).attr('src', customSrc);
                    if (variation.image.full_src) {
                        $(this).attr('data-large_image', variation.image.full_src);
                        $(this).closest('a').attr('href', variation.image.full_src);
                    }
                    if (variation.image.srcset) {
                        $(this).attr('srcset', variation.image.srcset);
                    } else {
                        $(this).removeAttr('srcset');
                    }
                });

                // Hide bullet dots
                $gallery.addClass('variation-selected');
            });

            // -------------------------------------------------------------
            // 3. When Variation Selection is Cleared / Reset
            // -------------------------------------------------------------
            $form.on('reset_data hide_variation', function () {
                isVariationActive = false;

                // Restore original parent product image
                if (originalData.src) {
                    $gallery.find('.woocommerce-product-gallery__image:first-child img, .clone:first-child img, .flex-active-slide img').each(function () {
                        $(this).attr('src', originalData.src);
                        if (originalData.large) {
                            $(this).attr('data-large_image', originalData.large);
                            $(this).closest('a').attr('href', originalData.href);
                        }
                        if (originalData.srcset) {
                            $(this).attr('srcset', originalData.srcset);
                        } else {
                            $(this).removeAttr('srcset');
                        }
                    });
                }

                // Restore bullet dots & restart auto-slide
                $gallery.removeClass('variation-selected');
                startAutoSlide();
            });
        }
    });
    </script>
    <?php
});