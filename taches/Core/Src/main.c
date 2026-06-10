/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;

TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
TIM_HandleTypeDef htim4;

UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_TIM1_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_ADC1_Init(void);
static void MX_TIM3_Init(void);
static void MX_TIM4_Init(void);
static void MX_TIM2_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
#define IN1_PIN  GPIO_PIN_4   // direction avant

#define IN_PORT  GPIOA
#define PWM_MAX  2099
#define VITESSE_MAX_RPM  250   // vitesse max du moteur (consigne 250 tr/min -> PWM max)

uint32_t counter = 0;
uint32_t valeur_brute = 0;
uint32_t valeur_courant_brute = 0;
float tension_volts = 0.0f;
float tension_courant = 0.0f;
float courant = 0.0f;
int16_t  count_precedent = 0;
volatile  int32_t  vitesse_rpm    = 0;
volatile uint8_t flag_1s = 0;
volatile uint8_t flag_100ms = 0;
volatile uint8_t sens = 0;
static int32_t position_precedente=0;
static uint32_t last_index_tick = 0;
static uint32_t tau=0;
static uint32_t temp2=0;
static uint32_t now=0;
uint16_t adc_buffer[2];

int tour;
volatile static int32_t count_actuel;


#define RESOLUTION_ENCODEUR  500
#define RAPPORT_REDUCTION    16

// Reception UART (commandes envoyees par l'IHM)
uint8_t rx_byte;
uint8_t rx_buffer[50];
uint8_t rx_index = 0;

// Controle du moteur depuis l'IHM (PC)
volatile uint8_t motor_running = 0;
volatile int32_t consigne_vitesse_rpm = 150;
volatile uint32_t current_pwm = 0;

void moteur_sens(uint8_t sens);

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */


  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_TIM1_Init();
  MX_USART2_UART_Init();
  MX_ADC1_Init();
  MX_TIM3_Init();
  MX_TIM4_Init();
  MX_TIM2_Init();
  /* USER CODE BEGIN 2 */
  HAL_TIM_Encoder_Start(&htim3, TIM_CHANNEL_ALL);

  // Timer 1ms pour les tâches périodiques
  HAL_TIM_Base_Start_IT(&htim1);

  HAL_TIM_Base_Start_IT(&htim2);

  // Direction moteur : AVANT (IN1=1, IN2=0)
  HAL_GPIO_WritePin(IN_PORT, IN1_PIN, 1);


  // Démarrer le PWM sur TIM3 Channel 1 (PA6)
  HAL_TIM_PWM_Start(&htim4, TIM_CHANNEL_1);


  // Duty cycle initial à 50%
  __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_1, 500);
  HAL_ADC_Start_DMA(&hadc1,(uint32_t*)adc_buffer, 2);

  // Demarrer la reception UART par interruption (commandes de l'IHM)
  HAL_UART_Receive_IT(&huart2, &rx_byte, 1);

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	  if(flag_1s)
	  	      {
	  	          flag_1s = 0;

	  	             // Tâche 1 : LED blink
	  	            // HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
	  	       // HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);


	  	             // Tâche 2 : lecture ADC (potentiomètre → consigne vitesse)


	  	             valeur_brute= adc_buffer[0];
	  	               valeur_courant_brute = adc_buffer[1];



	  	             tension_volts = valeur_brute * 3.3f / 4095.0f;
	  	             tension_courant=valeur_courant_brute * 3.3f / 4095.0f;
	  	             courant=(tension_courant/0.05f)/200.0f;



	  	             // PWM pilote par la consigne recue de l'IHM (START/STOP/SPEED)
	  	             uint32_t duty = current_pwm;
	  	             __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_1, duty);


	  	             // Tâche 3 : UART
	  	             char msg[120];
	  	             int partie_entiere = (int)tension_volts;
	  	             int partie_decimale = (int)((tension_volts - partie_entiere) * 100);

	  	           int partie_entiere_courant = (int)courant;
	  	           int partie_decimale_courant =
	  	                   (int)((courant - partie_entiere_courant) * 100);
	  	         sprintf(msg,
	  	                 "ADC:%u  Tension:%d.%02dV  Courant:%d.%02dA  tau:%u  PWM:%lu  Vitesse:%ld RPM\r\n",
	  	                 (unsigned int)valeur_brute,
	  	                 partie_entiere,
	  	                 partie_decimale,
	  	                 partie_entiere_courant,
	  	                 partie_decimale_courant,
	  	                 tau,
	  	                 duty,
	  	                 vitesse_rpm);



	  	            /* sprintf(msg, "ADC:%u  PWM:%lu  Count:%u  Delta:%d  Vitesse:%ld RPM\r\n",
	  	                         (unsigned int)valeur_brute,
	  	                         duty,
	  	                         (unsigned int)__HAL_TIM_GET_COUNTER(&htim4),
	  	                         (int)delta,
	  	                         vitesse_rpm);*/
	  	             HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);

	    }
	  	   if(flag_100ms)
	        {
	  		  if(vitesse_rpm!=0 && now==0){

	  			 now = HAL_GetTick();

	  		  }





	  		int sens_encodeur = __HAL_TIM_IS_TIM_COUNTING_DOWN(&htim3);
	            flag_100ms = 0;
	             count_actuel = (int32_t)__HAL_TIM_GET_COUNTER(&htim3);
	            int32_t delta = count_actuel - count_precedent;

	            // correction overflow 16 bits
	            if(delta > 32767) delta -= 65536;
	            if(delta < -32768) delta += 65536;

	            count_precedent = count_actuel;

	            vitesse_rpm = (delta * 600) / (RESOLUTION_ENCODEUR *4* RAPPORT_REDUCTION);






	            if(sens_encodeur){
	            	vitesse_rpm*=-1;

	                	}
	            if(vitesse_rpm>=218 && temp2==0){
	           	            	temp2=HAL_GetTick();


	           	            }

	           	            if(now != 0 && temp2 != 0)
	           	            {
	           	                tau = temp2 - now;
	           	            }


	  			/*int sens_encodeur = __HAL_TIM_IS_TIM_COUNTING_DOWN(&htim4);


	  			    	 count_actuel = (int32_t)__HAL_TIM_GET_COUNTER(&htim4);

	  			    	if(!sens_encodeur){
	  			    		tour++;
	  			    		__HAL_TIM_SET_COUNTER(&htim4, 0);

	  			    	}
	  			    	else{
	  			    		tour--;
	  			    		__HAL_TIM_SET_COUNTER(&htim4, 2000);

	  			    	}
	  			    	int32_t position=tour*RESOLUTION_ENCODEUR*4 + count_actuel;

	  			    	   /* vitesse_rpm = ((position - position_precedente) ) / (4*RESOLUTION_ENCODEUR*RAPPORT_REDUCTION*60*0.1 );
	  			    	vitesse_rpm = (int32_t)((float)(position - position_precedente)* 60.0f
	  			    		  			    	                / (4.0f * RESOLUTION_ENCODEUR * RAPPORT_REDUCTION * 0.1f));
	  			    	    position_precedente=position;*/




	    }
	    }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 16;
  RCC_OscInitStruct.PLL.PLLN = 336;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Configure the global features of the ADC (Clock, Resolution, Data Alignment and number of conversion)
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode = ENABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 2;
  hadc1.Init.DMAContinuousRequests = ENABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
  */
  sConfig.Channel = ADC_CHANNEL_0;
  sConfig.Rank = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_3CYCLES;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
  */
  sConfig.Channel = ADC_CHANNEL_1;
  sConfig.Rank = 2;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(void)
{

  /* USER CODE BEGIN TIM1_Init 0 */

  /* USER CODE END TIM1_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 8399;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = 9;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */

}

/**
  * @brief TIM2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM2_Init(void)
{

  /* USER CODE BEGIN TIM2_Init 0 */

  /* USER CODE END TIM2_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM2_Init 1 */

  /* USER CODE END TIM2_Init 1 */
  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 8399;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = 9;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim2) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim2, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM2_Init 2 */

  /* USER CODE END TIM2_Init 2 */

}

/**
  * @brief TIM3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM3_Init(void)
{

  /* USER CODE BEGIN TIM3_Init 0 */

  /* USER CODE END TIM3_Init 0 */

  TIM_Encoder_InitTypeDef sConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM3_Init 1 */

  /* USER CODE END TIM3_Init 1 */
  htim3.Instance = TIM3;
  htim3.Init.Prescaler = 0;
  htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim3.Init.Period = 65535;
  htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  sConfig.EncoderMode = TIM_ENCODERMODE_TI12;
  sConfig.IC1Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC1Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC1Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC1Filter = 0;
  sConfig.IC2Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC2Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC2Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC2Filter = 0;
  if (HAL_TIM_Encoder_Init(&htim3, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM3_Init 2 */

  /* USER CODE END TIM3_Init 2 */

}

/**
  * @brief TIM4 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM4_Init(void)
{

  /* USER CODE BEGIN TIM4_Init 0 */

  /* USER CODE END TIM4_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};

  /* USER CODE BEGIN TIM4_Init 1 */

  /* USER CODE END TIM4_Init 1 */
  htim4.Instance = TIM4;
  htim4.Init.Prescaler = 0;
  htim4.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim4.Init.Period = 2099;
  htim4.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim4.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim4) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim4, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_Init(&htim4) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim4, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim4, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM4_Init 2 */

  /* USER CODE END TIM4_Init 2 */
  HAL_TIM_MspPostInit(&htim4);

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA2_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA2_Stream0_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA2_Stream0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA2_Stream0_IRQn);

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_7, GPIO_PIN_RESET);

  /*Configure GPIO pin : PC13 */
  GPIO_InitStruct.Pin = GPIO_PIN_13;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pins : PA4 PA5 PA7 */
  GPIO_InitStruct.Pin = GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_7;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pin : PA9 */
  GPIO_InitStruct.Pin = GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /* EXTI interrupt init*/
  HAL_NVIC_SetPriority(EXTI9_5_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);

  HAL_NVIC_SetPriority(EXTI15_10_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
volatile int comp;

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if(htim->Instance == TIM1)
    {
        counter++;

        if(counter >= 1000) // toutes les secondes
        {
        	 HAL_ADC_Start_DMA(&hadc1,(uint32_t*)adc_buffer, 2);
        	flag_1s=1;
            counter = 0;





        }
    }
    else if(htim->Instance == TIM2)
      {
    	comp++;
    	  if(comp >= 100) // toutes les 100 millisecondes
    	        {
    	        	flag_100ms=1;
    	            comp = 0;


      }
}
}
void moteur_sens(uint8_t sens)
{
    // HIGH = arrière, LOW = avant
    HAL_GPIO_WritePin(IN_PORT, IN1_PIN, (sens ? 1 : 0));
}
volatile uint32_t last_press = 0;

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{

	uint32_t now;
	uint32_t now_moteur;
	uint32_t dt;

	int sens_encodeur = __HAL_TIM_IS_TIM_COUNTING_DOWN(&htim4);
    if(GPIO_Pin == GPIO_PIN_13)
    {
         now_moteur = HAL_GetTick();

        if((now_moteur - last_press) > 200)
        {
            last_press = now_moteur;
            sens = !sens;
            moteur_sens(sens);
        }
    }
    /*else if(GPIO_Pin == GPIO_PIN_9){
    	 now = HAL_GetTick();
    	 dt = now - last_index_tick;
    	if(dt == 0) dt = 1;
    	 count_actuel = (int32_t)__HAL_TIM_GET_COUNTER(&htim4);

    	if(!sens_encodeur){
    		tour++;
    		__HAL_TIM_SET_COUNTER(&htim4, 0);

    	}
    	else{
    		tour--;
    		__HAL_TIM_SET_COUNTER(&htim4, 2000);

    	}
    	int32_t position=tour*RESOLUTION_ENCODEUR*4 + count_actuel;

    	    vitesse_rpm = ((position - position_precedente) * 60000) / (4*RESOLUTION_ENCODEUR*RAPPORT_REDUCTION * dt);
    	    position_precedente=position;
    	    last_index_tick = now;

    }*/



}

// Reception des commandes envoyees par l'IHM (START/STOP/DIR/SPEED)
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        if (rx_byte == '\n' || rx_byte == '\r')
        {
            rx_buffer[rx_index] = '\0'; // Fin de chaine

            if (rx_index > 0)
            {
                if (strncmp((char*)rx_buffer, "START", 5) == 0)
                {
                    motor_running = 1;
                    current_pwm = (consigne_vitesse_rpm * PWM_MAX) / VITESSE_MAX_RPM;
                    if (current_pwm > PWM_MAX) current_pwm = PWM_MAX;
                    if (current_pwm == 0) current_pwm = 200; // petite rotation si consigne 0
                }
                else if (strncmp((char*)rx_buffer, "STOP", 4) == 0)
                {
                    motor_running = 0;
                    current_pwm = 0; // arret : PWM a 0
                }
                else if (strncmp((char*)rx_buffer, "DIR:GAUCHE", 10) == 0)
                {
                    sens = 1;
                    moteur_sens(sens);
                }
                else if (strncmp((char*)rx_buffer, "DIR:DROITE", 10) == 0)
                {
                    sens = 0;
                    moteur_sens(sens);
                }
                else if (strncmp((char*)rx_buffer, "SPEED:", 6) == 0)
                {
                    int vitesse;
                    if (sscanf((char*)rx_buffer + 6, "%d", &vitesse) == 1)
                    {
                        // borner la consigne a [0, VITESSE_MAX_RPM]
                        if (vitesse < 0) vitesse = 0;
                        if (vitesse > VITESSE_MAX_RPM) vitesse = VITESSE_MAX_RPM;
                        consigne_vitesse_rpm = vitesse;
                        if (motor_running)
                        {
                            current_pwm = (consigne_vitesse_rpm * PWM_MAX) / VITESSE_MAX_RPM;
                            if (current_pwm > PWM_MAX) current_pwm = PWM_MAX;
                        }
                    }
                }
            }

            rx_index = 0; // reinitialiser pour la prochaine commande
        }
        else
        {
            if (rx_index < sizeof(rx_buffer) - 1)
            {
                rx_buffer[rx_index++] = rx_byte;
            }
        }

        // Relancer la reception du prochain octet
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
    }
}


/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
